import pandas as pd
from pycparser import parse_file
from pycparser import c_ast
import sys
sys.path.extend(['.', '..'])

def get_Decl_info(node):
	id_type_record =[node.name, node.type.type.names[0], node.coord]
	return id_type_record

def lookup_var_type(df, var):
	assert hasattr(var, 'name')
	id=var.name
	id_record = df.loc[df['id'] == id]
	""" the ID should be unique """
	assert len(id_record) == 1
	id_type = id_record.iloc[0]['type']
	return id_type

def df_insert_row(df, row):
	df.loc[len(df)] = row

def cls_name(node):
	return node.__class__.__name__

class EmitVisitor(c_ast.NodeVisitor):
	def __init__(self):
		self.symbol_table = pd.DataFrame(columns=['id','type','src'])

		""" use the tuple of operand and id type as the key to rule dict """
		self.binop_prod_rule={
			('+', 'vectorf', 'vectorf') : 'axpby',
			('-', 'vectorf', 'vectorf') : 'axpby',
			('<', 'vectorf', 'vectorf') : 'ceil',
			('>', 'vectorf', 'vectorf') : 'floor',
			('*', 'vectorf', 'vectorf') : 'dot',

			('*', 'float', 'vectorf') : 'axpby_frac',

			('*', 'matrixf', 'vectorf') : 'spmv',

			('+', 'float', 'float') : 'scalar_op',
			('-', 'float', 'float') : 'scalar_op',
			('*', 'float', 'float') : 'scalar_op',
			('/', 'float', 'float') : 'scalar_op',
		}

		self.inst_out_type={
			'axpby': 'vectorf',
			'ceil': 'vectorf',
			'floor': 'vectorf',
			'dot':'float',
			'axpby_frac': 'vectorf',
			'spmv':'vectorf',
			'scalar_op':'float',
		}

		""" binary op temp var counter """ 
		self.temp_var_idx=0

		""" buffer to hold fractions of axpby""" 
		self.axpby_buffer={'s_a': 0.0,
							'v_x':None,
							's_b':0.0,
							'v_y':None,
							'frac_num':0}

	def add_axpby_frac(self, scalar, vector):
		assert self.axpby_buffer['frac_num'] < 2, \
		"buffer full: {}, {}".format(self.axpby_buffer['v_x'],
                       self.axpby_buffer['v_y'])

		if self.axpby_buffer['frac_num'] == 0:
			self.axpby_buffer['s_a']=scalar
			self.axpby_buffer['v_x']=vector
		elif self.axpby_buffer['frac_num'] == 1:
			self.axpby_buffer['s_b']=scalar
			self.axpby_buffer['v_y']=vector

		self.axpby_buffer['frac_num'] += 1

	def emit_axpby_buffer(self, result_name):
		assert self.axpby_buffer['frac_num'] <= 2
		assert self.axpby_buffer['frac_num'] > 0

		print("{} = axpby [ {} * {} + {} * {} ]".format(result_name,
                                                  self.axpby_buffer['s_a'],
                                                  self.axpby_buffer['v_x'],
                                                  self.axpby_buffer['s_b'],
                                                  self.axpby_buffer['v_y']))

		""" TODO: 1. eliminate common subexpression
			2. Decide VB address L0, L1,... or R0, R1, ...
		"""

		""" clear the buffer after emitting """ 
		self.axpby_buffer['s_a']=0.0
		self.axpby_buffer['v_x']=None
		self.axpby_buffer['s_b']=0.0
		self.axpby_buffer['v_y']=None
		self.axpby_buffer['frac_num']=0

	def temp_var_info(self, var_type, node):
		if not hasattr(node, 'name'):
			temp_name ='temp-'+str(self.temp_var_idx)
			self.temp_var_idx += 1
			node.name=temp_name
			df_insert_row(self.symbol_table, [node.name, var_type, node.coord])
		else:
			""" the result of the binop has been declared, 
			check if the declared type and the result type are the same """ 
			decl_type = lookup_var_type(self.symbol_table, node)
			assert decl_type == var_type
		
	def visit_Decl(self, node):
		""" gather ID, type info from decl stmt"""
		df_insert_row(self.symbol_table, get_Decl_info(node))

	def visit_Constant(self, node):
		self.temp_var_info('float', node)

	def visit_BinaryOp(self, node):
		for c in node:
			self.visit(c)
		""" choose machine idiom based on l-type and r-type """
		left_type = lookup_var_type(self.symbol_table, node.left)
		right_type = lookup_var_type(self.symbol_table, node.right)
		prod_head = (node.op, left_type, right_type)
		emit_inst = self.binop_prod_rule.get(prod_head)
		assert emit_inst is not None

		result_type = self.inst_out_type.get(emit_inst)
		self.temp_var_info(result_type, node)

		if emit_inst == 'axpby_frac':
			""" fraction buffer filled flag """
			self.add_axpby_frac(node.left.name, node.right.name)
			node.axpby_frac_flag = True
		elif emit_inst == 'axpby':
			if not hasattr(node.left, 'axpby_frac_flag'):	
				self.add_axpby_frac(1.0, node.left.name)

			if not hasattr(node.right, 'axpby_frac_flag'):	
				if node.op == '-':
					fill_scalar = -1.0
				else:
					fill_scalar = 1.0

				self.add_axpby_frac(fill_scalar, node.right.name)

			self.emit_axpby_buffer(node.name)
		else:
			print(emit_inst, node.left.name, node.right.name, node.name)

	def visit_Assignment(self, node):
		""" using the assigment value instead of temp var as name""" 
		node.rvalue.name = node.lvalue.name

		for c in node:
			self.visit(c)

		if self.axpby_buffer['frac_num'] > 0:
			self.emit_axpby_buffer(node.lvalue.name)

if __name__ == "__main__":
	filename='./osqp_alg_desc.c'
	ast = parse_file(filename, use_cpp=False)
	# ast.show(showcoord=False)
	main_stmts = ast.ext[0].body.children()

	ev = EmitVisitor()
	for idx, stmt in enumerate(main_stmts):
		ev.visit(stmt[1])
	# print(ev.symbol_table)
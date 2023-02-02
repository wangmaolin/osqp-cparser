# The C Compiler for RSQP instruction set

## Overview
This compiler targets the instruction set of RSQP architecture.
The source language is a modified version of C. 
Two new data type "vectorf" and "matrixf" are added to represent "OSQPVectorf" and "OSQPMatrix" in the OSQP source code.
The arithmetic function of OSQPvectorf and OSQPmatrix are replaced with reloaded operators. 
For example the following code shows how to define 2 vectors and compute a linear combination of them.

``` C
float scalar_a, scalar_b;
vectorf vec_x, vec_y, vec_z;

vec_z = scalar_a * vec_x + scalar_b * vec_b;
```

The RSQP architecture has an instruction "axpby" for computing the linear combination of vectors.
After compilation, an "axpby" instruction will be emitted for the above assignment statement. 

## Requirements
pandas

## An Example
The file `osqp_alg_desc.c` shows a partial description of the OSQP algorithm. 
Run the command `python emit_rsqp_ir.py` will emit the following IRs which will be used for machine executable generation.
```
scalar_op temp-1 settings_alpha temp-2
work_x = axpby [ settings_alpha * work_xtilde_view + temp-2 * work_x_prev ]
work_delta_x = axpby [ 1.0 * work_x + -1.0 * work_x_prev ]
temp-5 = axpby [ settings_alpha * work_ztilde_view + 1.0 * work_z ]
scalar_op temp-6 settings_alpha temp-7
work_z = axpby [ temp-7 * work_z_prev + 1.0 * temp-5 ]
scalar_op temp-10 settings_alpha temp-11
temp-13 = axpby [ settings_alpha * work_ztilde_view + temp-11 * work_z_prev ]
work_z = axpby [ work_rho_inv * work_y + 1.0 * temp-13 ]
ceil work_z work_data_u work_z
floor work_z work_data_l work_z
scalar_op temp-16 settings_alpha temp-17
temp-19 = axpby [ settings_alpha * work_ztilde_view + temp-17 * work_z_prev ]
work_delta_y = axpby [ temp-20 * work_z + 1.0 * temp-19 ]
work_delta_y = axpby [ settings_rho * work_delta_y + 0.0 * None ]
work_y = axpby [ 1.0 * work_y + -1.0 * work_delta_y ]
```

## TODO
### Common Subexpression Elimination
Scan for repeated expressions of vector linear combination 
### Vector Buffers Allocation
Assign the variable and temp IDs to Vector Buffers. 
There are two VBs in the RSQP architecture and each VB can store N vectors.
The "axpby" instruction requires the two operands to be at different VBs.
Smart VB allocation can help reduce the movement of the same vector between 2 VBs.


## Acknowledgment
The front end of the compiler is based on the pycparser: 
https://github.com/eliben/pycparser

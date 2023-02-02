int main()
{
	/* ----- declare all the vectors and scalars ----- */
	float settings_alpha, work_rho_inv, settings_rho;

	/* The source language is a modified version of C. 
	data type "vectorf" and "matrixf" are added. */
	vectorf work_x, work_x_prev, work_delta_x, work_xtilde_view;
	vectorf work_y, work_y_prev, work_delta_y;
	vectorf work_z, work_z_prev, work_ztilde_view;
	vectorf work_data_u, work_data_l;
	matrixf mat_P, mat_A, mat_At;
	/* ----- update xz_tilde PCG loop----- */


	/* ----- update x -----*/
	work_x = settings_alpha * work_xtilde_view+(1.0 - settings_alpha) * work_x_prev;
	work_delta_x = work_x - work_x_prev;

	/* ----- update z -----*/
	work_z = work_z + settings_alpha * work_ztilde_view + (1.0-settings_alpha) * work_z_prev;
	work_z = settings_alpha * work_ztilde_view + (1.0-settings_alpha) * work_z_prev + work_rho_inv * work_y;

	/* clip operation*/
	work_z = work_z < work_data_u;
	work_z = work_z > work_data_l;

	/* ----- update y -----*/
	work_delta_y = settings_alpha * work_ztilde_view + (1.0 - settings_alpha) * work_z_prev - 1.0* work_z;
	work_delta_y = settings_rho * work_delta_y;
	work_y = work_y - work_delta_y;

	/* check for termination*/

	/*update rho*/

	/*compute obj*/

	return 0;	
}
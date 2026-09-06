import os
import pyvista as pv
import pandas as pd
import math
import utils_CAD as utils_CAD
import numpy as np
import time
from scipy.spatial import cKDTree

'''
    @ Update 0803 jeff
    - KDTREE algorithm.

'''

def Voronoi_tesselation_KDTREE(model, mesh):
    '''
    KDTREE algorithm

    Note Mesh should be quadratic Tetrahedron.

    input:
    mesh: read by meshio
    model: class instance having (case_index and parameter_csv_path)
        self.case_index = case_index # case id, should be int.
        self.parameter_csv_path = parameter_csv_path

    output: new unstructured grid with calcification with physical tag 8
    '''

    #read the parameters from the vessel_model instance.
    fraction = model.vessel_model.fraction
    skew_axial = model.vessel_model.ca_axial_skewness
    skew_shoulder = model.vessel_model.ca_shoulder_skewness
    fc_av_th = model.vessel_model.fc_av_th
    d_fc_ca = model.vessel_model.d_fc_ca
    strength_axial = model.vessel_model.ca_axial_strength
    strength_circum = model.vessel_model.ca_shoulder_strength

    #tag for the subdomain, lipid, and calcification, defined in gmsh.
    subdomain_tag = 10
    lipid_tag = 2
    ca_tag = 8
    
    subdomain_mask = (mesh.cell_data["gmsh:physical"] == subdomain_tag) & (mesh.celltypes == 24)
    subdomain_cells_indices  = np.where(subdomain_mask)[0]
    
    #2. Now derive (# of cal) = (# of tetra) * fraction
    cal_num = round(len(subdomain_cells_indices ) * fraction)
    # print(f"fraction: {fraction}")
    # print(f"# of cal: {cal_num}\n")

    #3. get the z_max of the subdomain from the gmsh.
    submesh = mesh.extract_cells(subdomain_cells_indices)
    z_max = submesh.points[:, 2].max()
    z_seed   = skew_axial * z_max


    #4. calculate θ_seed from lipid_half_angle(z = z_seed) and the distance from the lumen_centere
    θ_lipid_arc_half = utils_CAD.alpha_theta(model.vessel_model, z_seed) #rad
    θ_seed_half = θ_lipid_arc_half * skew_shoulder

    #5. calculate the x, y coordinate of the seed_point
    # distance between the lumen_center and the seed_point 
    # (big assumption seed point is the closests to the lumen_center in the subdomain, divided by d_fc_ca)
    d_lumen_seed = utils_CAD.radius_lumen(model.vessel_model, z_seed) + fc_av_th + d_fc_ca
    x_seed = d_lumen_seed * math.cos(θ_seed_half)
    y_seed = d_lumen_seed * math.sin(θ_seed_half) + utils_CAD.y_center_lumen(model.vessel_model, z_seed)
    # print(f"x_seed: {x_seed}, y_seed: {y_seed}, z_seed: {z_seed}\n")
    
    #7. Find the tetra element that contains the seed_point.
    seed_point = np.array([x_seed, y_seed, z_seed])
    seed_cell_id = -1
    status = ""

    if submesh.n_cells > 0:
        local_cell_id = submesh.find_containing_cell(seed_point)
        original_ids_in_submesh = submesh.cell_data['vtkOriginalCellIds']
        
        if local_cell_id != -1:
            status = "point is in the subdomain"
            seed_cell_id = original_ids_in_submesh[local_cell_id]
        else:
            status = "closest cell in the subdomain"
            local_closest_cell_id = submesh.find_closest_cell(seed_point)
            seed_cell_id = original_ids_in_submesh[local_closest_cell_id]

    print(f"\nSEED_CELL_ID: {seed_cell_id}")
    print(f"SEED_STATUS: {status}")
    print(f"SEED_POINT: {seed_point}\n")



    ############################################################
    ######### Propagation algorithm from the KDTREE ############
    ############################################################
    start_time = time.time()
    calibrated_cells_original_ids = []

    if cal_num > 0:
        print(f"\nStarting KD-Tree based propagation...")

        # --- Parameters to control propagation shape ---
        # When weight is larger, distance is scaled down in that direction,
        # leading to more propagation in that direction
        # So for more axial propagation, we want axial_weight_factor to be larger
        axial_weight_factor = strength_axial
        circum_weight_factor = strength_circum

        # --- 1. prepare the data: extract the cell centers of the subdomain ---
        subdomain_cell_centers = mesh.cell_centers().points[subdomain_cells_indices]

        # --- 2. transform the coordinates: apply the weight to the coordinates ---
        # to make the general euclidean distance search to be like the weighted distance search,
        # we scale the coordinates by sqrt(weight)
        # Distance^2 ≈ w_c*(dx^2+dy^2) + w_a*dz^2
        w_axial_sqrt = np.sqrt(axial_weight_factor)
        w_circum_sqrt = np.sqrt(circum_weight_factor)
        
        transformed_centers = np.copy(subdomain_cell_centers)
        transformed_centers[:, 0:2] *= w_circum_sqrt # x, y (circumferential direction)
        transformed_centers[:, 2]   *= w_axial_sqrt   # z (axial direction)

        # --- 3. create the KDTree ---
        # create the KDTree with the transformed cell centers
        kdtree = cKDTree(transformed_centers)

        # --- 4. transform the seed point and query ---
        # transform the seed point with the same weight
        transformed_seed_point = np.copy(seed_point)
        transformed_seed_point[0:2] *= w_circum_sqrt
        transformed_seed_point[2]   *= w_axial_sqrt
        
        # query the cal_num nearest neighbors in the KD-Tree
        distances, indices = kdtree.query(transformed_seed_point, k=cal_num)

        # --- 5. map the result: convert the original cell IDs ---
        valid_indices = indices[np.isfinite(distances)] # filter the valid indices
        calibrated_cells_original_ids = subdomain_cells_indices[valid_indices]

        end_time = time.time()
        print(f"KD-Tree search completed in {end_time - start_time:.4f} seconds.")
        print(f"Selected {len(calibrated_cells_original_ids)} cells for calcification.")
        
        # Assign calcification tag (8) to the selected cells
        mesh.cell_data["gmsh:physical"][calibrated_cells_original_ids] = ca_tag # allocate new ca_index = 8


    else:
        print("cal_num is zero. No cells will be calcified.")



    #9. Change the tag = 10(lipid inside the subdomain) to tag = 2 since lipid tag is 2.
    lipid_mask = mesh.cell_data["gmsh:physical"] == subdomain_tag
    mesh.cell_data["gmsh:physical"][lipid_mask] = lipid_tag


    #10. Calculate the dependent variables(Total fraction, ca_length, Maximum cal arc angle)

    #10.1. Caculate Total fraction
    ca_mask = (mesh.cell_data["gmsh:physical"] == ca_tag) & (mesh.celltypes == 24) # Calcification mask
    ca_cells_indices  = np.where(ca_mask)[0]
    
    lipid_mask = (mesh.cell_data["gmsh:physical"] == lipid_tag) & (mesh.celltypes == 24) # Lipid mask
    lipid_cells_indices = np.where(lipid_mask)[0]

    total_fraction = len(ca_cells_indices) / (len(ca_cells_indices) + len(lipid_cells_indices))
    #print(f"total_fraction: {total_fraction}")

    
    #10.2. get the z_max of the subdomain from the gmsh.
    if len(ca_cells_indices) > 0:
        submesh = mesh.extract_cells(ca_cells_indices)
        z_max = submesh.points[:, 2].max()
        z_min = submesh.points[:, 2].min()
        ca_length = z_max - z_min
        #print(f"ca_length: {ca_length}")
    else:
        print("No calcification cells found. Setting ca_length to 0.")
        ca_length = 0.0

    #10.3. Maximum cal arc angle
    lumen_center = np.array([0, utils_CAD.y_center_lumen(model.vessel_model, z_seed), z_seed])
    seed_axis = seed_point - lumen_center
    
    # Extract calcification submesh points
    if len(ca_cells_indices) > 0:
        ca_submesh = mesh.extract_cells(ca_cells_indices)
        ca_points = ca_submesh.points
        
        # Filter points where abs(z - z_seed) < 0.01
        z_filter = np.abs(ca_points[:, 2] - z_seed) < 0.01
        filtered_points = ca_points[z_filter]
    else:
        filtered_points = np.array([])
    

    if len(filtered_points) > 0:
        # Calculate vectors from lumen_center to filtered points
        vectors_to_points = filtered_points - lumen_center
        
        # Normalize vectors(point - lumen_center, and seed_axis)
        vectors_to_points_norm = vectors_to_points / np.linalg.norm(vectors_to_points, axis=1, keepdims=True)
        seed_axis_norm = seed_axis / np.linalg.norm(seed_axis)
        
        # Calculate angles using dot product and cross product for sign
        dot_products = np.dot(vectors_to_points_norm, seed_axis_norm)
        # Clamp dot products to [-1, 1] to avoid numerical issues
        dot_products = np.clip(dot_products, -1.0, 1.0)
        angles = np.arccos(dot_products)
        
        # Calculate cross products to determine sign (clockwise/counterclockwise)
        cross_products = np.cross(vectors_to_points_norm, seed_axis_norm)
        # Use z-component of cross product to determine sign
        sign_determinant = np.dot(cross_products, np.array([0, 0, 1]))
        angles = np.where(sign_determinant >= 0, angles, -angles)
        
        # Convert to degrees
        angles_deg = np.degrees(angles)
        
        # Find maximum and minimum angles
        max_angle = np.max(angles_deg)
        min_angle = np.min(angles_deg)
        ca_arc = max_angle - min_angle
        
        print(f"Maximum cal arc angle: {max_angle:.2f}°")
        print(f"Minimum cal arc angle: {min_angle:.2f}°")
        print(f"Cal arc angle range: {max_angle - min_angle:.2f}°")

        #Now save the cal_arc_angle to the parameter_csv_path
        parameter_df = pd.read_csv(model.parameter_csv_path)
        par_dict = parameter_df.iloc[model.case_index].to_dict()

        #Now save the cal_arc_angle to the parameter_csv_path
        par_dict["total_fraction"] = round(total_fraction, 4)
        par_dict["ca_length"] = round(ca_length, 4)
        par_dict["ca_arc"] = round(ca_arc, 4)
        
        # Create a series with same index as dataframe to ensure alignment
        new_row = pd.Series(par_dict, index=parameter_df.columns)
        parameter_df.iloc[model.case_index] = new_row
        parameter_df.to_csv(model.parameter_csv_path, index=False)

    else:
        print("No points found within z tolerance for cal arc angle calculation")
        max_angle = 0.0
        min_angle = 0.0


    return mesh
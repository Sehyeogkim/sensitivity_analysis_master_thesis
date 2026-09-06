import gmsh
import meshio
import numpy as np
import os
import multiprocessing
import time
import utils_gmsh as utils

'''
Last updated 0813 jeff
    - OFFSET based meshing(0808)
    - 10mins timeout meshing(0813)
'''



def gmshing_solid(lumen_stp_path, solid_stp_path, lipid_stp_path, fc_stp_path, ca_stp_path, save_folder_path, nproc = 5, 
                  Terminal_display = True, Save_vtu = False, mesh_size = 0.04, show_mesh = True):


    start_time = time.time()
    gmsh.initialize()
    gmsh.model.add("Stenosis Model")

    #Terminal display setting
    if Terminal_display:   
        gmsh.option.setNumber("General.Terminal", 1)   
    else:
        gmsh.option.setNumber("General.Verbosity", 0) 

    #STEP1: lipid n fc -> new fc
    lipid = gmsh.model.occ.importShapes(lipid_stp_path)[0]   #[(3,1)]
    gmsh.model.occ.synchronize()

    fc    = gmsh.model.occ.importShapes(fc_stp_path)[0]     #[(3,2)]
    gmsh.model.occ.synchronize()

    gmsh.model.occ.intersect([lipid], [fc], removeObject = False, removeTool = True) 
    gmsh.model.occ.synchronize()

    gmsh.model.occ.removeAllDuplicates() # Intersection of the lipid and fc varies the lipid core.
    gmsh.model.occ.synchronize()
    lipid = (3,3)


    #Check if the entities are in the volumes
    volumes = gmsh.model.getEntities(3)
    if lipid and fc in volumes:
        print("STEP1 complete, lipid and fc are in the volumes")
    else:
        raise Exception("STEP1 Failed.")



    #STEP2: lipid - fc_soffset -> ca.
    fc_offset = gmsh.model.occ.importShapes(ca_stp_path)[0] # (3,4)
    gmsh.model.occ.synchronize()

    #Intersection of the lipid and fc_offset
    intersect = gmsh.model.occ.intersect([lipid], [fc_offset], removeObject = False, removeTool = True)
    print(f"Intersect: {intersect}")
    gmsh.model.occ.synchronize()

    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()

    lipid = (3,4)
    ca = (3,5)


    #Check if the entities are in the volumes
    volumes = gmsh.model.getEntities(3)
    if lipid and fc and ca in volumes:
        print("STEP2 complete, lipid,fc and ca are in the volumes")
    else:
        raise Exception("STEP2 Failed.")
    
    '''
    fc - (3,2)
    ca - (3,4)
    lipid - (3,5)
    '''

    # #STEP3 fc - lumen -> new fc
    lumen = gmsh.model.occ.importShapes(lumen_stp_path)[0] #(3,6)
    gmsh.model.occ.synchronize()

    gmsh.model.occ.cut([fc], [lumen], removeObject = True, removeTool = False)
    gmsh.model.occ.synchronize()

    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()


    volumes = gmsh.model.getEntities(3)
    if fc and lumen in volumes:
        print("STEP3 complete, fc and solid are in the volumes")
    else:
        raise Exception("STEP3 Failed.")
    


    #STEP4 solid - (lipid+fc+lumen) -> new solid

    solid = gmsh.model.occ.importShapes(solid_stp_path)[0] #(3,8)
    gmsh.model.occ.synchronize()

    gmsh.model.occ.cut([solid], [lipid, fc, lumen], removeObject = False, removeTool = False)
    gmsh.model.occ.synchronize()

    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()


    
    volumes = gmsh.model.getEntities(3)
    if lipid and fc and lumen and solid in volumes:
        print("STEP4 complete, solid is in the volumes")
    else:
        raise Exception("STEP4 Failed.")




    ############################################
    ############# PHYSICAL TAGGING #############
    ############################################
    gmsh.model.addPhysicalGroup(3, [solid[1]], tag=1, name="solid")
    gmsh.model.addPhysicalGroup(3, [lipid[1]], tag=2, name="lipid")
    gmsh.model.addPhysicalGroup(3, [fc[1]], tag=3, name="fc")
    gmsh.model.addPhysicalGroup(3, [ca[1]], tag=10, name="ca")



    # Extract volume tags from lumen
    lumen_volume_tags = [lumen[1]]


    # Get the boundary surfaces between solid and fc fc = (3,7)
    fc_surfaces    = [abs(s[1]) for s in gmsh.model.getBoundary([fc],    oriented=False)]
    solid_surfaces = [abs(s[1]) for s in gmsh.model.getBoundary([solid], oriented=False)]
    lipid_surfaces = [abs(s[1]) for s in gmsh.model.getBoundary([lipid], oriented=False)]

    
    wall_in_fc_tags    = utils.find_wall_surfaces(fc_surfaces,    lumen_volume_tags)
    wall_in_solid_tags = utils.find_wall_surfaces(solid_surfaces, lumen_volume_tags)  
    gmsh.model.occ.synchronize()

    lipid_in_fc_tags = list(set(lipid_surfaces) & set(fc_surfaces))
    gmsh.model.addPhysicalGroup(2, wall_in_fc_tags, tag=5, name="wall_in_fc")
    gmsh.model.addPhysicalGroup(2, wall_in_solid_tags, tag=4, name="wall_in_solid")
    gmsh.model.addPhysicalGroup(2, lipid_in_fc_tags, tag=7, name="lipid_in_fc")
    gmsh.model.occ.synchronize()
     


    all_solid_surfaces = gmsh.model.getBoundary([solid], oriented=False)
    #print("Solid surfaces:", all_solid_surfaces)

    # Get z coordinates of surface centers to identify inlet/outlet
    surface_centers = []
    for surface in all_solid_surfaces:
        com = gmsh.model.occ.getCenterOfMass(surface[0], abs(surface[1]))
        surface_centers.append((surface, com[2]))  # Store surface and its z coordinate
    
    # Sort by z coordinate
    surface_centers.sort(key=lambda x: x[1])
    
    # First surface (minimum z) is inlet (side1), last surface (maximum z) is outlet (side2)
    side1_surface = surface_centers[0][0] # (dim = 2 , tag)
    side2_surface = surface_centers[-1][0] # (dim = 2 , tag)


    # Add physical groups for inlet and outlet
    gmsh.model.addPhysicalGroup(2, [abs(side1_surface[1]), abs(side2_surface[1])], 
                                    tag=6, name="Two_sides")
    gmsh.model.occ.synchronize()


    #remove lumen
    gmsh.model.occ.remove([lumen])
    gmsh.model.occ.synchronize()



    #CHECK The physical groups are all in the list
    physical_groups = gmsh.model.getPhysicalGroups(3)
    for (dim, tag) in physical_groups:
        if tag not in [1,2,3,10]:
            raise Exception(f"Physical group {tag} is not in the list")
    

    if show_mesh:
        utils.gmsh_display(exit = True)
        return


   
    ####################################
    ############# MESHING ##############
    ####################################
    '''

    B. Meshing Procedures
        1. Generate distance field (Criteria: wall_in_fc  or all_fc_faces)
        2. Generate threshold field from the distance field
        3. Set mesh options as below.
        4. Generate mesh
        5. save as msh file
        6. save as vtu file(0.1 scaled)
    
    #Mesh options need to be considered
        1. Fibrou cap mesh size - 0.05, other wise 0.1
        2. Number of CPU cores - 32 if available > 32, otherwise 10.
        3. Smoothing must be used in order to get a posiive Jacobi ratio.
        4. Quadratic tetra
    
    [Mesh Algorithm Types]
    1	Delaunay	        The fastest, handles complex mesh size fields well (default)
    4	Frontal	            Front-based, generates cleaner elements for boundary shapes
    5	Frontal Delaunay	Mix of Delaunay and Frontal for higher quality
    6	Frontal Hex	        Specify on hexa Generation 
    7	MMG3D	            External MMG library based adaptive mesh reconstruction
    9	R-tree	            Spatial partitioning tree based (large-scale parallel partitioning, etc.)

    2D
    1: MeshAdapt, 2: Automatic, 3: Initial mesh only, 
    5: Delaunay,  6: Frontal-Delaunay, 7: BAMG, 8: Frontal-Delaunay for Quads, 
    9: Packing of Parallelograms, 11: Quasi-structured Quad

    3D
    1: Delaunay, 3: Initial mesh only, 
    4: Frontal, 7: MMG3D, 9: R-tree, 10: HXT

    '''
    
    #CPU core setting
    print(f"Number of going to be used CPU cores on gmshing: {nproc}")
    utils.slash_lines()
    gmsh.option.setNumber("General.NumThreads", nproc)  # Leave some cores free for system
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", nproc)  # Leave some cores free for system
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", nproc)  # Use 12 threads for 3D meshing
    gmsh.model.occ.synchronize()

    # Add box field around lipid core for refined meshing
    box_field = gmsh.model.mesh.field.add("Box")
    gmsh.model.mesh.field.setNumber(box_field, "Thickness", 3.0)  # Transition layer thickness
    gmsh.model.mesh.field.setNumber(box_field, "VIn", mesh_size)  # Fine mesh size inside box
    gmsh.model.mesh.field.setNumber(box_field, "VOut", 0.2)   # Regular mesh size outside box
    
    # Get bounding box of lipid volume (lipid2)
    gmsh.model.mesh.field.setNumber(box_field, "XMin", -10.0)
    gmsh.model.mesh.field.setNumber(box_field, "XMax", 10.0)
    gmsh.model.mesh.field.setNumber(box_field, "YMin", -10.0)
    gmsh.model.mesh.field.setNumber(box_field, "YMax", 10.0)
    gmsh.model.mesh.field.setNumber(box_field, "ZMin", -5.0)
    gmsh.model.mesh.field.setNumber(box_field, "ZMax", 5.0)

    # Set box field as background field
    gmsh.model.mesh.field.setAsBackgroundMesh(box_field)

    gmsh.option.setNumber("Mesh.ElementOrder"       , 2)   # quadratic
    gmsh.option.setNumber("Mesh.Algorithm"          , 5)   # 2D Delaunay 5
    gmsh.option.setNumber("Mesh.Algorithm3D"        , 1)   # 3D Delaunay 1
    gmsh.option.setNumber("Mesh.Smoothing"          , 5)   # Laplacian smoothing
    gmsh.model.occ.synchronize()

    #Generate mesh
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize('HighOrder')
    utils.check_mesh_quality(0)

    #save as mesh
    gmsh_save_path = os.path.join(save_folder_path, "total_solid.msh") #unscaled solid file.
    gmsh.write(gmsh_save_path)
    gmsh.finalize()

    utils.get_mesh_info(gmsh_save_path) # .msh file info by meshio
    print("!!!Gmsh mesh completely saved on:", gmsh_save_path)
    print(f"\nTime taken for gmshing: {time.time() - start_time} seconds\n")
    

    if Save_vtu:
        #just for visualization, save as scaled vtu file.
        mesh = meshio.read(gmsh_save_path)
        mesh.points *= 0.1
        vtu_save_path = gmsh_save_path.replace('.msh', '.vtu')
        meshio.write(vtu_save_path, mesh)
        print("!!!Vtu file(scaled) completely saved on:", vtu_save_path)

    return gmsh_save_path





if __name__ == "__main__":

    non_meshed_list = []
    skipped_mesh = [7, 12, 15, 23, 56, 58, 71, 79, 84, 112, 129] # skip these mesh.
    too_many_mesh = [24, 26, 91, 114] # need to be done further

    for i in too_many_mesh:

        try:
            folder_path = f"/home/jeff/project/30.Meeting_data/model_0809/case_{i}"   
            lumen_path = os.path.join(folder_path, "lumen.stp")
            solid_path = os.path.join(folder_path, "solid.stp")
            lipid_path = os.path.join(folder_path, "lipid.stp")
            fc_path = os.path.join(folder_path, "fc.stp")
            ca_path = os.path.join(folder_path, "fc_offset.stp")
            error_log_path = os.path.join(folder_path, "meshing_errors.txt")
            
            print(f"\n\n************Processing case {i}:************\n")
            vtu_path = os.path.join(folder_path, "total_solid.vtu")
            if os.path.exists(vtu_path):
                print(f"Vtu file already exists for case {i}, skipping...")
                continue
            
            # Create error log file if it doesn't exist
            if not os.path.exists(error_log_path):
                open(error_log_path, 'w').close()

            # Start a timer to check if meshing takes too long
            start = time.time()
            timeout_seconds = 600 # 10mins
            mesh_size = 0.035
            show_mesh = False
            nproc = 10

            mesh_process = multiprocessing.Process(
            target=gmshing_solid,
            args=(lumen_path, solid_path, lipid_path, fc_path, ca_path, folder_path, 
                  nproc, True, True, mesh_size, show_mesh)
            )

            mesh_process.start()
            mesh_process.join(timeout=timeout_seconds)
            if mesh_process.is_alive():
                error_msg = f"Meshing took longer than {timeout_seconds} seconds timeout"
                with open(error_log_path, "a") as f:
                    f.write(f"Case {i}: Timeout Error - {error_msg}\n\n")
                raise TimeoutError(error_msg)
            print(f"Meshing took {time.time() - start} seconds")
                

        except Exception as e:
            print(f"Error in case {i}: {e}")
            print(f"Skipping case {i} and continuing with next case...\n")
            non_meshed_list.append(i)
                
            # Write error to file
            with open(error_log_path, "a") as f:
                f.write(f"Case {i}: {type(e).__name__} - {str(e)}\n\n")
            continue


    print(f"Non-meshed cases: {non_meshed_list}")
    print(f"Total non-meshed cases: {len(non_meshed_list)}")
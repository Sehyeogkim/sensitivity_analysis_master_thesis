# -*- coding: utf-8 -*-
import ansys.mapdl.core as pymapdl
import pandas as pd
import os
import numpy as np
import pyvista as pv
import time
from ansys.mapdl.core import LOG
from ansys.mapdl.reader import save_as_archive
import meshio

from Voronoi_tesselation_KDTREE import Voronoi_tesselation_KDTREE
from main_CAD import VesselModel

#utils.
import utils_prep as utils_prep
import utils_bc as utils_bc
import utils_post as utils_post
import utils_gmsh as utils_gmsh

class PYMAPDL_worker():

    def __init__(self, case_index: int, wall_folder_path: str, ansys_exec_dir: str, 
                 parameter_csv_path: str, port_num: int = 50052, nproc: int = 30, is_calcification = True):
        
        self.case_index = case_index # case id, should be int.
        self.wall_folder_path = wall_folder_path
        self.ansys_exec_dir = ansys_exec_dir
        self.parameter_csv_path = parameter_csv_path
        self.port_num = port_num
        self.nproc = nproc
        self.is_calcification = is_calcification # whether or not to apply calcification.

        #will be defined further.
        self.bc_type = ""
        self.casename = ""
        self.cdb_path = ""
        self.calcification_fraction = 0.0

        #Read Calcifcation parameters from the csv file and create the vessel model instance.
        parameter_df = pd.read_csv(self.parameter_csv_path)
        par_dict = parameter_df.iloc[self.case_index].to_dict()

        PI = par_dict["PI"]
        alpha = par_dict["alpha"]

        lipid_length = par_dict["lipid_length"]
        fc_av_th = par_dict["fc_av_th"]

        d_fc_ca = par_dict["d_fc_ca"]
        fraction = par_dict["fraction"]

        skew_axial = par_dict["ca_axial_skewness"]   
        skew_shoulder = par_dict["ca_shoulder_skewness"]
        
        strength_axial = par_dict["ca_axial_strength"]
        strength_circum = par_dict["ca_shoulder_strength"]

        self.vessel_model = VesselModel(PI, alpha, lipid_length, fc_av_th, d_fc_ca, fraction, skew_axial, skew_shoulder, strength_axial, strength_circum)
    

    def pymapdl_launch(self, display_info = True):
 
        # Shut down any existing MAPDL instance on this port
        try:
            existing_mapdl = pymapdl.Mapdl(port=self.port_num)
            existing_mapdl.exit()
            print(f"Killing existing MAPDL instance on port {self.port_num}, plz wait for 5s to ensure MAPDL instance is fully terminated")            
            time.sleep(5)  # Wait 5 seconds to ensure MAPDL instance is fully terminated
        except:
            print("No existing MAPDL instance on this port")

        #Launch MAPDL
        self.mapdl = pymapdl.launch_mapdl(
                jobname = f"{self.case_index}",
                exec_file="/opt/cvbml/softwares/ansys_inc/v251/ansys/bin/ansys251",
                run_location = self.ansys_exec_dir,
                loglevel="ERROR", #Print out only ERROR
                override = True,
                port = self.port_num,
                nproc = self.nproc #number of processors.
            )
        print(f"New MAPDL launched successfully on port {self.mapdl.port}")
        self.mapdl.units("CGS")
        
        #MAPDL INFO
        if display_info:
            utils_prep.section_title(f"ANSYS MAPDL VER: {self.mapdl.version}")
            print(self.mapdl)
            print("current direcotry:", self.mapdl.directory)
            print(f"Number of CPU: {self.mapdl.get_value('ACTIVE', 0, 'NUMCPU')}")
            print("mapdl ip:", self.mapdl.ip)
            print("mapdl port:", self.mapdl.port)
            utils_prep.slash_lines()

        return None
    

    def pymapdl_msh_to_cdb(self, gmsh_path, save_vtu = False):
        '''
        Convert .msh file to .cdb file.

        @jeff 0708
        if self.macro_cal is True, the macro calcification will be applied to the mesh.
        '''
        mesh = pv.read_meshio(gmsh_path)
        mesh.points *= 0.1 #scale down cuz of inventor.
        self.nodes_by_tag, _ = utils_prep.surface_nid_dic(mesh, Linear = False, Terminal_display = False)
        
        #Voronoi tessellation (update the mesh including calcification)
        if self.is_calcification:
            mesh = Voronoi_tesselation_KDTREE(self, mesh)

        ####Don't need actually ####
        gmsh_filename = os.path.basename(gmsh_path) #total_solid.msh
        cdb_filename = gmsh_filename.replace(".msh", ".cdb") #total_solid.msh -> total_solid.cdb
        cdb_path = os.path.join(self.ansys_exec_dir, cdb_filename)
        save_as_archive(cdb_path, mesh)

        if save_vtu:
            vtu_path = os.path.join(self.ansys_exec_dir, f"total_solid.vtu")
            mesh.save(vtu_path)
            print(f"Completely saved {vtu_path}")

        return cdb_path

    def pymapdl_prep_bc(self):

        #start the prep7 read the .cdb file.
        self.mapdl.prep7()
        cdb_name = os.path.basename(self.cdb_path)
        self.mapdl.cdread("db", cdb_name) #name or path?? check.
        self.mapdl.nlgeom("OFF")
        self.mapdl.shpp("OFF")

        #check geo and mesh info.
        utils_prep.section_title("Geo and Mesh info")
        print(self.mapdl.mesh)
        self.mapdl.allsel()

        print("set(self.mapdl.mesh.material_type):", set(self.mapdl.mesh.material_type))
        print("set(self.mapdl.mesh.etype):", set(self.mapdl.mesh.etype))

        wall_in_vessel_tag = 4
        wall_in_fc_tag = 5
        sides_tag = 6
        lipid_in_fc_tag = 7 # new tag updated 0528 jeff

        #Fixed support BC on the two sides which were tagged as 6. (0.15s)
        sides_tag = 6
        fix_time = time.time()
        utils_prep.fix_bc_from_nid_list(self.mapdl, self.nodes_by_tag[sides_tag])
        print(f"Fixed support BC time: {time.time() - fix_time:.2f} seconds")

        #generate Component block for each surface.
        cm_display = False
        cm_time = time.time()
        utils_prep.Create_cm_from_nid_list(self.mapdl, self.nodes_by_tag[wall_in_vessel_tag], "WALL_IN_VESSEL", cm_display)
        utils_prep.Create_cm_from_nid_list(self.mapdl, self.nodes_by_tag[wall_in_fc_tag], "WALL_IN_FC", cm_display)
        utils_prep.Create_cm_from_nid_list(self.mapdl, self.nodes_by_tag[lipid_in_fc_tag], "LIPID_IN_FC", cm_display) # updated 0528 jeff
        print(f"Create CM for wall_in_vessel, wall_in_fc, and lipid_in_fc time: {time.time() - cm_time:.2f} seconds")
        
        #Define Element type 7 for Total Traction.
        self.mapdl.et(7,"SURF154")
        self.mapdl.keyopt(7,2,1) # face,1,2,3 -> local x,y,z, direction
        self.mapdl.keyopt(7,4,0) # 8 nodes.
        self.mapdl.keyopt(7,7,1)
        self.mapdl.keyopt(7,11,2)

        #Define a new local coordinate(num 14, arbitrary) for etype 7(element local coordinate)
        self.mapdl.local(14, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.mapdl.csys(0) 

        #Generate ETYPE 7 surface Mesh in order to apply Total traction.
        walls = ["WALL_IN_FC", "WALL_IN_VESSEL"]
        for wall in walls:
            self.mapdl.cmsel(type_= 'S', name = wall, entity = 'NODE')
            self.mapdl.type(7)
            self.mapdl.esurf()

        self.mapdl.esel('S', 'TYPE', '', 7)
        self.mapdl.emodif('all', 'ESYS', 14)
        wall_elem_array = self.mapdl.mesh.elem

        self.mapdl.nsle() #select all nodes attached to the currently selected element.
        wall_node_ids = self.mapdl.mesh.nnum #wall node ids.
        wall_node_coord = self.mapdl.mesh.nodes #wall node point coordinates.
        self.mapdl.allsel()

        #Apply Total traction to the wall.
        '''
        1. Interpolate the wall data.
        2. Apply the traction to the wall.
        '''
        print(f"\nApplying {self.bc_type} BC...")
        wall_csv_path = os.path.join(self.wall_folder_path, f"wall_{self.bc_type}.csv") #wall_peak.csv, wall_av.csv, wall_low.csv
        wall_interpol_df = utils_bc.Interpolate_wall_data(wall_csv_path, wall_node_ids, wall_node_coord, Total_Traction = True)


        apply_time = time.time()
        txt_path = os.path.join(self.wall_folder_path, f"apply_traction_{self.bc_type}.txt")
        utils_bc.Apply_Traction(self.mapdl, wall_interpol_df, wall_elem_array, Total_Traction = True, txt_path = txt_path)
        print(f"Apply traction {self.bc_type} time: {time.time() - apply_time:.2f} seconds")
        
        self.mapdl.finish() #finish the prep7


        #Save the mesh and BC info.
        self.mapdl.allsel()
        self.mapdl.cdwrite('All',f'{self.casename}','cdb')


        return
    
    def pymapdl_prep_mat(self):
    
        '''
        Step6. Define Material Properties
        '''
        self.mapdl.prep7() #Must restart the prep7 after defining new jobname.
        self.mapdl.nlgeom("OFF")
        self.mapdl.shpp("OFF")


        mat_case_df = pd.read_csv(self.parameter_csv_path)
        mat_case_row = mat_case_df.loc[self.case_index]

        #material properties for vessel, lipid, fc, ca.(Linear Elastic Assmuption)
        materials = {1: "vessel", 2: "lipid", 3: "fc"} # physical tag : mat name
        
        #if there is calcification, add ca to the materials dictionary.
        if self.is_calcification:
            materials[8] = "ca"

        for mat_id, mat_name in materials.items():

            if mat_id == 1 :
                E = mat_case_row[f'E_{mat_name}']
            else: #vessel is the reference material and the other materials are defined by the ratio of the vessel.
                E = mat_case_row[f'E_{mat_name}_ratio'] * mat_case_row[f'E_vessel']
            
            rho = mat_case_row[f'rho_{mat_name}']
            v = 0.49
            self.mapdl.mp('DENS', mat_id, rho)  # Density in g/cm³
            self.mapdl.mp('EX', mat_id, E)  # Elastic modulus in dynes/cm² (e.g., 1 MPa = 10^6 dynes/cm²)
            self.mapdl.mp('NUXY', mat_id, v)  # Poisson's ratio
            

        self.mapdl.allsel()
        utils_prep.section_title(f"Material ID of {self.casename}")
        print(self.mapdl.mplist())

        self.mapdl.finish() #finish the prep

        return
    
    def pymapdl_solve(self):
        '''
        static solver.
        '''
        start_solver_time = time.time()
        utils_prep.section_title(f"Solve {self.casename}") #self.casename = case_{index}_{bc_type}
        
        self.mapdl.allsel() 
        self.mapdl.run("/SOLU", verbose = True) #start the solver
        self.mapdl.antype("STATIC")
        self.mapdl.nlgeom("OFF") #turm off the non-linear
        self.mapdl.eqslv(lab = 'PCG', toler = 1e-8) #preconditioned conjugate gradient solver.
        
        self.mapdl.time(1) # set the end_time
        self.mapdl.autots("ON") #auto time stepping.
        self.mapdl.nsubst(nsbstp = 0.1, nsdbmn = 1, nsbmx = 10, carry = "OFF")
        self.mapdl.kbc(0) #ramped Load
        self.mapdl.allsel()

        self.mapdl.solve(verbose = True)
        self.mapdl.finish()

        print(f"Total simulation time: {time.time() - start_solver_time:.2f} seconds")
        self.mapdl.db.save(f'{self.casename}.db')

        #clean up the useless data.
        #utils_prep.wipe_out_useless_data(self.ansys_exec_dir)

    def pymapdl_post_eqv_fc(self):
        '''
        Purpose: Generate .vtu file from the .rst file and .db file.(inside of the mapdl.)
        Save: (FC) Nodal displacement, EQV, Elemental EQV will be saved as .vtu file.
        '''
        self.mapdl.post1() #start the post processing.
        self.mapdl.set(1,1)

        #Select the total FC elements which is defined as mat_id 3.
        self.mapdl.esel('S', 'MAT', '', 3)
        elem_fc = np.array(self.mapdl.mesh.elem)                                 #element connectivity
        elem_eqv_fc = np.array(self.mapdl.post_processing.element_stress('EQV')) #elemental eqv stress


        #select all nodes contatined in the selected element.
        self.mapdl.nsle()
        nids_fc = np.array(self.mapdl.mesh.nnum)                               #node ids of fc elements.
        ncoords_fc = np.array(self.mapdl.mesh.nodes)                           #node coordinates of fc elements.
        nodal_eqv_fc = np.array(self.mapdl.post_processing.nodal_eqv_stress()) #nodal eqv stress of fc elements.
        nodal_disp_fc = np.array(self.mapdl.post_processing.nodal_displacement('ALL'))

        #node ids of two surfaces of FC (WALL_IN_FC, LIPID_IN_FC)
        self.mapdl.cmsel(type_= 'S', name = "WALL_IN_FC", entity = 'NODE')
        nids_5 = np.array(self.mapdl.mesh.nnum) #physical tag 5
        self.mapdl.cmsel(type_= 'S', name = "LIPID_IN_FC", entity = 'NODE')
        nids_7 = np.array(self.mapdl.mesh.nnum) #physical tag 7

        #finish the post processing.
        self.mapdl.finish()

        #save as .vtu file.
        start_time = time.time()
        vtu_path = os.path.join(self.ansys_exec_dir, f"EQV_{self.casename}.vtu")
        utils_post.FC_EQV_save_as_vtu(elem_fc, nids_fc, ncoords_fc,              #data to define cells.
                                    elem_eqv_fc, nodal_eqv_fc, nodal_disp_fc,    #data to be saved.
                                    nids_5, nids_7, filepath=vtu_path)            #data for tagging each surface.
        print(f"Saved {self.casename} as vtu in {time.time() - start_time:.2f} seconds")
        
        return

    def pymapdl_post_eqv_all(self):
        '''
        Purpose: Generate .vtu file from the .rst file and .db file.(inside of the mapdl.)
        Save: (CA) Nodal displacement, EQV, Elemental EQV will be saved as .vtu file.
        !!For the lipid, ca and fc all of them are saved as .vtu file.
        @update 0708 jeff

        '''
        self.mapdl.post1() #start the post processing.
        self.mapdl.set(1,1)

        start_time = time.time()

        #Select the total FC elements which is defined as mat_id 3.
        self.mapdl.esel('S', 'MAT', '', 8) #ca
        self.mapdl.esel('A', 'MAT', '', 2) #lipid
        self.mapdl.esel('A', 'MAT', '', 3) #fc

        #extract the element and node info.
        elem_array = np.array(self.mapdl.mesh.elem)                           #element connectivity
        elem_eqv = np.array(self.mapdl.post_processing.element_stress('EQV')) #elemental eqv stress
        elem_mat = np.array(self.mapdl.mesh.material_type)
        
        self.mapdl.nsle()
        nids = np.array(self.mapdl.mesh.nnum)                               #node ids of fc elements.
        ncoords = np.array(self.mapdl.mesh.nodes)                           #node coordinates of fc elements.
        nodal_eqv = np.array(self.mapdl.post_processing.nodal_eqv_stress()) #nodal eqv stress of fc elements.
        nodal_disp = np.array(self.mapdl.post_processing.nodal_displacement('ALL'))

        #generate meshio mesh
        index_map = np.empty(nids.max()+1, dtype=int)
        index_map[nids] = np.arange(len(nids))
        corners = np.stack([elem_array[:, -10], elem_array[:, -9], elem_array[:, -8], elem_array[:, -7]], axis=1)
        cell_nodes = index_map[corners]
        
        nodal_eqv = nodal_eqv[index_map[nids]]
        nodal_disp = nodal_disp[index_map[nids]]
        
        mesh = meshio.Mesh(
            points=ncoords,
            cells=[("tetra", cell_nodes)],
            cell_data={"EQV":[elem_eqv], "Material_Type": [elem_mat]},
            point_data={"Nodal_EQV": nodal_eqv, "Displacement": nodal_disp}
        )

        vtu_path = os.path.join(self.ansys_exec_dir, f"Total_EQV_{self.casename}.vtu")
        meshio.write(vtu_path, mesh, file_format="vtu")
        self.mapdl.finish()

        print(f"Saved Total_EQV_{self.casename}.vtu in {time.time() - start_time:.2f} seconds")

        return

    def post_interest_region(self, save_folder_path, region_type = "surface"):
        '''
        Since above 'pymapdl_post_fc_eqv'function generates fc_EQV.vtu data, This function will extract 
        the av and max eqv on each interest surface from the above extracted vtu data.

        Interest surface:
        - lipid_in_fc tagged as 7(fc-lipid interface)
        - wall_in_fc  tagged as 5(fc-lumen interface)

        Av and Max EQV will be calculated at 3 regions(proximal, middle, distal) on each interest surface.
        The regions is divided along w/ the z coordinate.

        proximal: z < - z_criteria
        middle: - z_criteria < z < z_criteria
        distal: z > z_criteria

        The result will be saved as a following dictionary format:
        region_eqv =
            {
                '5': [[prox_avg, mid_avg, dist_avg], [prox_max, mid_max, dist_max], [max_node_id, max_nodal_eqv, max_region]],
                '7': [[prox_avg, mid_avg, dist_avg], [prox_max, mid_max, dist_max], [max_node_id, max_nodal_eqv, max_region]]
            }
        
        @update 0715 jeff
        Overall, This code combines peak, av, low data and generate peak av amp data.
        '''
        
        post_time = time.time()
        peak_vtu = os.path.join(self.ansys_exec_dir, f"EQV_case_{self.case_index}_peak.vtu")
        #av_vtu = os.path.join(self.ansys_exec_dir, f"EQV_case_{self.case_index}_av.vtu")
        #low_vtu = os.path.join(self.ansys_exec_dir, f"EQV_case_{self.case_index}_low.vtu")

        #generate amp_vtu file from peak and low.
        #amp_vtu = os.path.join(self.ansys_exec_dir, f"EQV_case_{self.case_index}_amp.vtu")
        #utils_post.generate_amp_vtu(peak_vtu, low_vtu, amp_vtu)
        
        #region eqv
        region_eqv = {} #new dictionary for each mat_id.
        rows = []
        #########################################################
        ###################   surface region   ##################
        #########################################################
        if region_type == "surface":
            region_eqv["peak"] = utils_post.vtu_to_surface_eqv(self.vessel_model.z_lipid, peak_vtu)
            #region_eqv["av"] = utils_post.vtu_to_surface_eqv(self.vessel_model.z_lipid, av_vtu)
            #region_eqv["amp"] = utils_post.vtu_to_surface_eqv(self.vessel_model.z_lipid, amp_vtu)
            #print("region_eqv", region_eqv)
            #save two surface data. back and forth of the fc.
            for bc_type in ["peak"]:
                for tag in [5]: # TAG 5: fc-lumen interface, TAG 7: fc-lipid interface
                    avgs, maxs, max_node_info = region_eqv[bc_type][tag]
                    row = {
                        'case_index': self.case_index,
                        'bc_type': bc_type,
                        #'tag': tag,
                        'Pro1_av': avgs[0],
                        'Pro2_av': avgs[1],
                        'Mid1_av': avgs[2],
                        'Mid2_av': avgs[3],
                        'Dis1_av': avgs[4],
                        'Dis2_av': avgs[5]
                        # 'Pro1_max': maxs[0],
                        # 'Pro2_max': maxs[1],
                        # 'Mid1_max': maxs[2],
                        # 'Mid2_max': maxs[3],
                        # 'Dis1_max': maxs[4],
                        # 'Dis2_max': maxs[5],
                        # 'Max_node_id': max_node_info[0],
                        # 'Max_nodal_eqv': max_node_info[1],
                        # 'Max_region': max_node_info[2],
                    }
                    rows.append(row)


    
        #########################################################
        ###################   volume region   ##################
        #########################################################        
            
        elif region_type == "volume":
            region_eqv["peak"] = utils_post.vtu_to_volume_eqv(self.vessel_model.z_lipid, peak_vtu)
            # region_eqv["av"] = utils_post.vtu_to_volume_eqv(self.vessel_model.z_lipid, av_vtu)
            # region_eqv["amp"] = utils_post.vtu_to_volume_eqv(self.vessel_model.z_lipid, amp_vtu)

            for bc_type in ["peak"]:
                avgs_list = region_eqv[bc_type]
                row = {
                    'case_index': self.case_index,
                    'bc_type': bc_type,
                    'Pro1_av': avgs_list[0],
                    'Pro2_av': avgs_list[1],
                    'Mid1_av': avgs_list[2],
                    'Mid2_av': avgs_list[3],
                    'Dis1_av': avgs_list[4],
                    'Dis2_av': avgs_list[5],
                }
                rows.append(row)
        else:
            raise ValueError(f"Invalid region_type: {region_type} should be 'surface' or 'volume'.")
           


        result_df = pd.DataFrame(rows)
        
        #Check if csv file exists and has header.
        result_csv_path = os.path.join(save_folder_path, f"result_fc_{region_type}.csv")
        if not os.path.exists(result_csv_path):
            result_df.to_csv(result_csv_path, index=False)
            print(f"Created {result_csv_path}")
        else:
            result_df.to_csv(result_csv_path, mode='a', header=False, index=False)
            print(f"Updated {result_csv_path}")

        print(f"Completed updated {result_csv_path} for {self.case_index} in {time.time() - post_time:.2f} seconds")



        return






if __name__ == "__main__":


    #Two parallel process range(151,225) , range(225, 300)
    for case_index in range(256,300): 
        working_dir = "/home/jeff/project/30.Meeting_data"
        wall_folder_path = "/home/jeff/project/30.Meeting_data/wall_data"
        ansys_exec_dir = f"/home/jeff/project/30.Meeting_data/model_0809/case_{case_index}"
        parameter_csv_path = "/home/jeff/project/30.Meeting_data/parameter_sample_300.csv"
        nproc = 15
        port_num = 50053

        #Check if the mesh and result file exist.
        vtu_path = os.path.join(ansys_exec_dir, f"total_solid.vtu")
        EQV_path = os.path.join(ansys_exec_dir, f"EQV_case_{case_index}_peak.vtu")
        
        if not os.path.exists(vtu_path):
            print(f"VTU file(total_solid.vtu) does not exist for case {case_index}, skipping...")
            continue
        if not os.path.exists(EQV_path):
            print(f"EQV_case_{case_index}_peak.vtu does not exist, skipping...")
            continue

        print(f"\n\n************Processing case {case_index}, port: {port_num}:************\n")
        #1. define the pymapdl_worker instance and launch the mapdl instance.
        pymapdl_worker = PYMAPDL_worker(case_index, wall_folder_path, ansys_exec_dir, parameter_csv_path, port_num, nproc)
        pymapdl_worker.pymapdl_launch()

        #2. Convert .msh  to .cdb + save the surface mesh info for the future bc setting.
        gmsh_path =  os.path.join(ansys_exec_dir, f"total_solid.msh") #./geo_id/total_solid.msh
        cdb_path = pymapdl_worker.pymapdl_msh_to_cdb(gmsh_path, save_vtu = True) # convert .msh to .cdb, return cdb_path
        pymapdl_worker.cdb_path = cdb_path

        #3. Apply the bc and solve the case.
        for bc_type in ["peak"]:
            pymapdl_worker.bc_type = bc_type
            pymapdl_worker.casename = f"case_{pymapdl_worker.case_index}_{pymapdl_worker.bc_type}"
            pymapdl_worker.mapdl.jobname = pymapdl_worker.casename
            
            #Pre processing
            pymapdl_worker.pymapdl_prep_bc()
            pymapdl_worker.pymapdl_prep_mat()

            #Solve the case.
            pymapdl_worker.pymapdl_solve()

            #Post processing
            pymapdl_worker.pymapdl_post_eqv_fc() # generate EQV_case_index_bc_type.vtu on each peak, av, low bc_type case.
            pymapdl_worker.pymapdl_post_eqv_all() # generate Total_EQV_case_index_bc_type.vtu on each peak, av, low bc_type case.
        
            pymapdl_worker.mapdl.clear() #clear the mapdl instance(important bnut not exit the mapdl instance.)

        pymapdl_worker.mapdl.exit()

        # 4. Post processing, read three different bc_type.vtu and generate final result file.   
        pymapdl_worker.post_interest_region(working_dir, region_type = "volume")
        pymapdl_worker.post_interest_region(working_dir, region_type = "surface")

        utils_prep.wipe_out_useless_data(ansys_exec_dir)



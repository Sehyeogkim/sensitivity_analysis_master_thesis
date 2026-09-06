import os

def check_gmsh():
    '''
    Check if the gmsh file is created.
    '''
    non_exist_case_ids = []
    folder_path = "/home/jeff/project/30.Meeting_data/model_0809"
    for case_id in range(150,300):
        case_id_path = os.path.join(folder_path, f"case_{case_id}")
        vtu_path = os.path.join(case_id_path, f"total_solid.vtu")
        if os.path.exists(vtu_path):
            pass
        else:
            non_exist_case_ids.append(case_id)
    print(f"length: {len(non_exist_case_ids)}")
    print(f"Non-exist case ids: {non_exist_case_ids}")
    
    # Write non-exist case IDs to file
    output_path = os.path.join(folder_path, "non_exist_cases.txt")
    with open(output_path, "w") as f:
        f.write("Cases missing VTU files:\n")
        f.write("=====================\n")
        for case_id in non_exist_case_ids:
            f.write(f"case_{case_id}\n")
    
    print(f"Non-exist cases written to: {output_path}")

def delete_non_useful_data():
    '''
    Delete the non-useful data.
    '''

    folder_path = "/home/jeff/project/30.Meeting_data/model_0809"
    for case_id in range(300):
        case_id_path = os.path.join(folder_path, f"case_{case_id}")
        if os.path.exists(case_id_path):
            for filename in os.listdir(case_id_path):
                filepath = os.path.join(case_id_path, filename)
                # Keep vtu, stp and msh files
                if filename.endswith(('.cdb', 'vtu', 'stp', 'msh')):
                    pass
                else:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        print(f"Removed {filepath}")

    

def check_vtu():
    '''
    Check if the simulation is completed.
    '''
    folder_path = "/home/jeff/project/30.Meeting_data/model_0809"
    check_list = []
    for case_id in range(150):
        case_id_path = os.path.join(folder_path, f"case_{case_id}")
        EQV_result_path = os.path.join(case_id_path, f"EQV_case_{case_id}_peak.vtu")
        mesh_vtu_path = os.path.join(case_id_path, f"total_solid.vtu")

        if os.path.exists(EQV_result_path):
            check_list.append(case_id)
        
        # if os.path.exists(mesh_vtu_path):
        #     import meshio
        #     mesh = meshio.read(mesh_vtu_path)
        #     n_cells = len(mesh.cells_dict['tetra10'])
        #     if n_cells > 6000000:
        #         print(f"Case {case_id}: {n_cells} cells")
        #         check_list.append((case_id, n_cells))
        
        else:
            continue


    print(f"length: {len(check_list)}")
    print(f"EQV result exist case ids: {check_list}")


    return


import pandas as pd
def check_csv_result():

    #read csv file and get all the values in the columne "case_index"
    volume_csv_path = "/home/jeff/project/30.Meeting_data/result_fc_volume.csv"
    surf_csv_path = "/home/jeff/project/30.Meeting_data/result_fc_surface.csv"
    para_csv_path = "/home/jeff/project/30.Meeting_data/parameter_sample_300.csv"

    volume_df = pd.read_csv(volume_csv_path)
    surface_df = pd.read_csv(surf_csv_path)
    para_df = pd.read_csv(para_csv_path)

    volume_case_index_list = volume_df["case_index"].tolist()
    surface_case_index_list = surface_df["case_index"].tolist()
    para_case_index_list = para_df["total_fraction"].tolist()
    

    non_result_list_volume = []
    non_result_list_surface = []
    csv_result_list=[]

    for index in range(300):
        if index not in volume_case_index_list:
            non_result_list_volume.append(index)
        if index not in surface_case_index_list:
            non_result_list_surface.append(index)
        
        if para_case_index_list[index] == 0:
            csv_result_list.append(index)
    
        

    print(f"Non-result volume case ids: {non_result_list_volume}")
    print(f"Volume length: {len(non_result_list_volume)}")
    print(f"Non-result surface case ids: {non_result_list_surface}")
    print(f"Surface length: {len(non_result_list_surface)}")

    return




def final_result():

    




    return




if __name__ == "__main__":
    #check_gmsh()
    #check_vtu()
    #check_csv_result()
    #check_simulation()
    delete_non_useful_data()
    #final_result()


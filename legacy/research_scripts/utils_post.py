import numpy as np
import math
import meshio
import pyvista as pv

class post_geo_model:
    
    def __init__(self, alpha, z_lesion = 1.0, r_min = 0.055, r_max = 0.1):
        
        #Should be read from teh geo_cases.csv
        self.alpha = alpha
        
        #Fixed parameters as long as lumen geo is fixed.
        self.z_lesion = z_lesion
        self.r_min = r_min
        self.r_max = r_max
        self.T = z_lesion
        self.z_lipid = 0.3 * z_lesion # lipid ratio is arbiitary but 0.3 is adequate

    def radius_lumen(self, z):
        '''
        radius of the lumen along the z axis.
        '''
        if abs(z) <= self.z_lesion:
            A = self.r_min - self.r_max
            B = self.r_min

            r = A * math.cos(2 * math.pi * z / self.T) + B -  self.y_center_lumen(z)
        else:
            r = self.r_max

        return r

    def y_center_lumen(self, z):
        '''
        y coordinate of the center of the lumen along the z axis.
        
        #cos function is used to self the lumen.
        T = self.lesion_length
        amplitude = -(self.r_max - self.r_min)
        '''
        A = -(self.r_max - self.r_min)
        if abs(z) <= self.z_lesion:
            return A / 2 + (A / 2) * math.cos(2 * math.pi * z / self.T)
        else:
            return 0
        
    def x_criteria(self):
        '''

        '''
        #parameters for x_criteria
        alpha_rad = math.radians(self.alpha)
        x_fc = self.radius_lumen(z = 0) * math.sin(0.5 * alpha_rad)

        if self.alpha > 180:
            x_critera = self.radius_lumen(z = 0)  * 1/3
        else:
            x_critera = x_fc * 1/3

        
        return x_critera

def FC_EQV_save_as_vtu(elem, nnum, nodes, elem_eqv, noda_eqv, nodal_disp, nids_5, nids_7, filepath="FC_EQV.vtu"):
    """
    This function is used to generate the FC EQV vtu file.
    - Elemental EQV and nodal EQV are saved in the vtu file.
    
    #Save the point array as the tag array.
    interfaec between lumen and fibrous cap -> nids_5 : tag 5
    interfaec between fibrous cap and lipid -> nids_7 : tag 7
    else : tag 0
    """
    # Build map from global node ID to local index
    index_map = np.empty(nnum.max()+1, dtype=int)
    index_map[nnum] = np.arange(len(nnum))
    
    # Extract connectivity (tetra corners) linear tetrahedron
    corners = np.stack([elem[:, -10], elem[:, -9], elem[:, -8], elem[:, -7]], axis=1)
    cell_nodes = index_map[corners]

    tags = np.zeros(len(nnum), dtype=int)
    
    for nid in nids_5:
        tags[index_map[nid]] = 5 #physical tag 5
    
    for nid in nids_7:
        tags[index_map[nid]] = 7 #physical tag 7


    #Nodal EQV
    nodal_eqv = noda_eqv[index_map[nnum]]
    nodal_disp = nodal_disp[index_map[nnum]]
    
    # Write VTU with nodal SPR data
    mesh = meshio.Mesh(
        points=nodes,
        cells=[("tetra", cell_nodes)],
        cell_data={"EQV":[elem_eqv]},
        point_data={"Group": tags, "Nodal_EQV": nodal_eqv, "Displacement": nodal_disp}
    )
    meshio.write(filepath, mesh, file_format="vtu")
    return



def generate_amp_vtu(peak_vtu_path: str, low_vtu_path: str, amp_vtu_path: str):
    '''
    generate amp_vtu file from peak_vtu and low_vtu.

    amp_vtu has nodal EQV data and element EQV data as well.
    '''
    peak_mesh = pv.read(peak_vtu_path)
    low_mesh = pv.read(low_vtu_path)
    peak_mesh.point_data["Nodal_EQV"] = peak_mesh.point_data["Nodal_EQV"] - low_mesh.point_data["Nodal_EQV"]
    peak_mesh.cell_data["EQV"] = peak_mesh.cell_data["EQV"] - low_mesh.cell_data["EQV"]
    peak_mesh.save(amp_vtu_path)
    return


def Extract_Nodal_EQV(mapdl, cm_name):
    '''
    @update 05/28 jeff
    Input: mapdl instance, and component name that nodes are grouped.

    Output: node_ids, node_coord, nodal_eqv_stress

    !!Caution, 
    - qudaratic nodes do not have EQV stress.
    '''

    #Node info
    mapdl.cmsel(type_= 'S', name = cm_name, entity = 'NODE')
    node_ids = np.array(mapdl.mesh.nnum) #wall node ids.
    node_coord = np.array(mapdl.mesh.nodes) #wall node point coordinates.
    nodal_eqv_stress = np.array(mapdl.post_processing.nodal_eqv_stress())

    # Get mask of non-zero stress values
    nonzero_mask = nodal_eqv_stress != 0
    
    # Apply mask to all arrays to keep only nodes with non-zero stress(Eliminate middle points info)
    node_ids = node_ids[nonzero_mask]
    node_coord = node_coord[nonzero_mask]
    nodal_eqv_stress = nodal_eqv_stress[nonzero_mask]

    print("node_ids", node_ids)
    print("node_coord", node_coord)
    print("nodal_eqv_stress", nodal_eqv_stress)

    return node_ids, node_coord, nodal_eqv_stress





def get_node_index(node_ids, node_id):
    """Return the index of node_id in node_ids array."""
    return np.where(node_ids == node_id)[0][0]

def triangle_area(coords):
    """Calculate area of a triangle given 3 (x, y, z) coordinates."""
    a = coords[1] - coords[0]
    b = coords[2] - coords[0]
    return 0.5 * np.linalg.norm(np.cross(a, b))

def element_centroid(coords):
    """Calculate centroid of a triangle given 3 (x, y, z) coordinates."""
    return np.mean(coords, axis=0)

def eid_list_sel(mapdl, eid_list):
    '''
    @update 05/27 jeff
    (usd on post procssing part.)
    This function is defined in order to select the element IDs in the eid_list.
    '''
    commands = []
    for i,eid in enumerate(eid_list):   
        if i == 0:
            cmd = f"esel, 'S', 'ELEM', ,{eid}"
        else:
            cmd = f"esel, 'A', 'ELEM', ,{eid}"
        commands.append(cmd)
    cmd_string = "\n".join(commands)
    mapdl.input_strings(cmd_string)
    return

def vtu_to_surface_eqv(z_lipid: float, vtu_path: str):
    """
    @update 0811 jeff
    Analyze surface triangles in a VTU file by node tag (5 and 7).
    For each tag, only consider triangles where all three nodes have the tag.
    
    #Algorithm
    For each region (pro1, pro2, mid1, mid2, dis1, dis2, by centroid z):
        - Compute area-weighted average and max surface elemental EQV (mean of nodal values per triangle).
    On top of that, find the node with the maximum nodal EQV for each tag and its region.

    Returns:
        dict: For each tag (5, 7), a list:
            [pro1_avg, pro2_avg, mid1_avg, mid2_avg, dis1_avg, dis2_avg],
            [pro1_max, pro2_max, mid1_max, mid2_max, dis1_max, dis2_max],
            (max_node_id, max_nodal_eqv, max_region)]
    """

    # 1) read file and extract surface.
    mesh = pv.read(vtu_path)

    #Extract surface
    surf = mesh.extract_surface()
    tris = surf.faces.reshape(-1, 4)[:, 1:]  # (n_tri, 3)
    pts = surf.points
    eqv = surf.point_data["Nodal_EQV"]
    tags = surf.point_data["Group"]

    results = {}
    for tag in [5]:
        # Only triangles where all three nodes have the tag
        mask = np.all(tags[tris] == tag, axis=1)
        tris_tag = tris[mask]

        # Prepare region stats
        region_stats = {
            "pro1": {"area": [], "eqv": []},
            "pro2": {"area": [], "eqv": []},
            "mid1": {"area": [], "eqv": []},
            "mid2": {"area": [], "eqv": []},
            "dis1": {"area": [], "eqv": []},
            "dis2": {"area": [], "eqv": []},
        }

        for tri in tris_tag:
            #tri = [n1, n2, n3] -> area, element eqv
            xyz = pts[tri]
            z_cent = xyz[:, 2].mean()

            #Determine the region along the z axis.
            if   z_cent > 0.75 * z_lipid:   region = None
            elif z_cent >  0.5 * z_lipid:   region = "dis2"
            elif z_cent > 0.25 * z_lipid:   region = "dis1"
            elif z_cent > 0:                region = "mid2"
            elif z_cent > -0.25 * z_lipid:  region = "mid1"
            elif z_cent >  -0.5 * z_lipid:  region = "pro2"
            elif z_cent > -0.75 * z_lipid:  region = "pro1"
            else: region = None

            #Pass the none case
            if region is None: continue

            #Calculate area and eqv
            v1 = xyz[1] - xyz[0]
            v2 = xyz[2] - xyz[0]
            area = 0.5 * np.linalg.norm(np.cross(v1, v2))
            eqv_val = eqv[tri].mean()  # or use centroid interpolation if you prefer

            region_stats[region]["area"].append(area)
            region_stats[region]["eqv"].append(eqv_val)


        #Now calculate the average and max eqv for each region.
        avg_list = []
        max_list = []
        for region in ("pro1", "pro2", "mid1", "mid2", "dis1", "dis2"):
            areas = np.array(region_stats[region]["area"])
            eqvs = np.array(region_stats[region]["eqv"])
            if areas.size > 0:
                avg = round(np.sum(eqvs * areas) / np.sum(areas), 2)
                mx = round(np.max(eqvs), 2)
            else:
                avg = 0.00
                mx = 0.00
            avg_list.append(avg)
            max_list.append(mx)

        # Find the node with the maximum nodal EQV for this tag
        node_inds = np.where(tags == tag)[0]
        if node_inds.size > 0:
            node_eqv = eqv[node_inds]
            imax = node_inds[np.argmax(node_eqv)]
            eqv_max = eqv[imax]
            z_node = pts[imax, 2]
            if   z_node > 0.75 * z_lipid: max_region = None
            elif z_node > 0.5 * z_lipid: max_region = "dis2"
            elif z_node > 0.25 * z_lipid: max_region = "dis1"
            elif z_node > 0:                   max_region = "mid2"
            elif z_node > -0.25 * z_lipid: max_region = "mid1"
            elif z_node > -0.5 * z_lipid: max_region = "pro2"
            elif z_node > -0.75 * z_lipid: max_region = "pro1"
            else:                              max_region = None
            max_node_info = (int(imax), float(eqv_max), max_region)
        else:
            max_node_info = (None, None, None)

        results[tag] = [avg_list, max_list, max_node_info]


    return results


#@updated 0801 jeff
def vtu_to_volume_eqv(z_lipid: float, vtu_path: str):
    """
    input: 
    - vtu_path to read 
    - z_lipid to classify the region.

    @update 0801 jeff
    Analyze volume tetrahedra in a Fibrous cap vtu file.
    
    #Algorithm
    For each region (pro1, pro2, mid1, mid2, dis1, dis2, by centroid z):
        - Compute volume and max surface elemental EQV (mean of nodal values per triangle).
    On top of that, find the node with the maximum nodal EQV for each tag and its region.

    Returns: single list
    [pro1_avg, pro2_avg, mid1_avg, mid2_avg, dis1_avg, dis2_avg]

    """

    mesh = pv.read_meshio(vtu_path)
    eqv = mesh.cell_data["EQV"]
    tetras = mesh.cells_dict[10]
    pts = mesh.points
   
    # Prepare region stats
    region_dict = {
        "pro1": {"volume": [], "eqv": []},
        "pro2": {"volume": [], "eqv": []},
        "mid1": {"volume": [], "eqv": []},
        "mid2": {"volume": [], "eqv": []},
        "dis1": {"volume": [], "eqv": []},
        "dis2": {"volume": [], "eqv": []},
    }

    #loop all tetra and calculate save the EQV data on each domain.
    for i, tetra in enumerate(tetras):
        #tetra = [n1, n2, n3, n4] -> volume, element eqv
        xyz = pts[tetra] # (4,3) each tetra node's point coordinates.
        z_cent = xyz[:, 2].mean() 

        #Determine the region along the z axis.
        if   z_cent > 0.75 * z_lipid:   region = None
        elif z_cent >  0.5 * z_lipid:   region = "dis2"
        elif z_cent > 0.25 * z_lipid:   region = "dis1"
        elif z_cent > 0:                region = "mid2"
        elif z_cent > -0.25 * z_lipid:  region = "mid1"
        elif z_cent >  -0.5 * z_lipid:  region = "pro2"
        elif z_cent > -0.75 * z_lipid:  region = "pro1"
        else: region = None

        #Pass the none case
        if region is None: continue

        #get the volume of the tetra
        v0, v1, v2, v3 = xyz[0], xyz[1], xyz[2], xyz[3]
        volume = abs(np.linalg.det([v1-v0, v2-v0, v3-v0])) / 6

        # Get stress value for this tetrahedron
        stress = eqv[i]

        region_dict[region]["volume"].append(volume)
        region_dict[region]["eqv"].append(stress)



    #Now calculate the average and max eqv for each region.
    avg_list = []
    for region in ("pro1", "pro2", "mid1", "mid2", "dis1", "dis2"):
        volume = np.array(region_dict[region]["volume"])
        eqvs = np.array(region_dict[region]["eqv"])
        if volume.size > 0:
            avg = round(np.sum(eqvs * volume) / np.sum(volume), 2)
        else:
            avg = 0.00
        avg_list.append(avg)



    return avg_list
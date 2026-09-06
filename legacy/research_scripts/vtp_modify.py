'''
#extract_TT.py
3. from the wall.vtp(including the inlet outlet cap and the wall)
- remove the inlet and outlet by ModelFaceID stored in the vtp file.
- calculate the nomral vector on each cell(wall) and save as cell_array on the vtp as 'normal'
- Change the cell_data into the point_data
- Now on each point they have pressure(scalar), r_inplane traction(vector) and normal(vector).
- Calculate the Total_tarction(vecotr) as a point array
- Total_traction = pressure * normal + r_inplane traction
- Save the csv file inclu/ (x,y,z coordinate and Total traction)
- Do this for two time step (peak and low)
'''

def extract_TT(vtp_path, save_path):
    pass

if __name__ == "__main__":
    vtp_path = "/home/jeff/project/33.lumen_modify/wall.vtp"
    save_path = "/home/jeff/project/33.lumen_modify/wall_TT.csv"
    extract_TT(vtp_path, save_path)


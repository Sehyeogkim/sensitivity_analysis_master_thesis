import math
'''
@ Update 0801 jeff
 - CAD model is required for the pymapdl simulation.
'''

class VesselModel:

    def __init__(self, 
                PI, alpha, 
                lipid_length, fc_av_th, 
                d_fc_ca, fraction, 
                ca_axial_skewness, ca_shoulder_skewness, 
                ca_axial_strength, ca_shoulder_strength,
                r_max = 0.1, r_min = 0.055, 
                lesion_length = 1.0, thick_ratio = 0.2, lumen_skewness = 0.0):
        
        ############################################################
        #Lumen parameters.
        self.r_max = r_max
        self.r_min = r_min
        self.lesion_length = lesion_length
        self.skewness = lumen_skewness  # [-1, 1]

        #Solid parameters.
        self.PI = PI 
        self.thick_ratio = thick_ratio # WALL_THICKNESS/ RADIUS = 0.2, DEFAULT

        #Lipid parameters.
        self.alpha = alpha
        self.lipid_length = lipid_length

        # Distance between the lipid circle at z = 0 and the solid wall. (for the calculatiozn of the stenosis area)
        self.lipid_wall_thickness = 1.5 * thick_ratio * r_min 

        #Fibrous cap parameters.
        self.fc_av_th = fc_av_th 

        #Calcifcaiton parameters. (Vornoli Tesslation method)
        self.d_fc_ca = d_fc_ca
        self.fraction = fraction
        self.ca_axial_skewness = ca_axial_skewness
        self.ca_shoulder_skewness = ca_shoulder_skewness
        self.ca_axial_strength = ca_axial_strength
        self.ca_shoulder_strength = ca_shoulder_strength
        ############################################################


        #Dependent parameters for further calcuations
        self.z_lipid = self.lipid_length / 2
        self.z_lesion = self.lesion_length / 2
        
        #Variables for the lumen skewness.
        self.z_peak = self.skewness * self.z_lesion # minimum Area z coordinate (varies depend on the lumen skewness)
        self.z_start = -2 * self.lesion_length # start point of the lumen
        self.z_end = 4 * self.lesion_length # end point of the lumen

        self.T        = self.lesion_length #Period of the sinousal functions that frequently defined in the CAD codes.
        self.r_ex     = self.r_max * (1 + self.thick_ratio) #External circle radius of the normal vessel.
        self.r_pos    = math.sqrt(self.PI) * self.r_ex # External circle Radius of the ''positive remodeled'' vessel. (for the calculation of the stenosis area)
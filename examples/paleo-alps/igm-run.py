#!/usr/bin/env python3

import tensorflow as tf
import math
from igm import igm
import numpy as np
from scipy.interpolate import interp1d
 
class igm(igm):

    def init_smb_signal(self):
        """
            Retrieve the Temperature difference from the EPICA signal
        """
        # load the EPICA signal from the official data
        ss = np.loadtxt('data-for-paleo-tuto/EDC_dD_temp_estim.tab',dtype=np.float32,skiprows=31)
        time = ss[:,1] * -1000  # extract time BP, chnage unit to yeat
        dT   = ss[:,3]          # extract the dT, i.e. global temp. difference
        self.dT =  interp1d(time,dT, fill_value=(dT[0], dT[-1]),bounds_error=False)

    def update_smb_signal(self):
        """
            mass balance 'signal'
        """

        # this serves to open the EPICA file (this is done only once at start)
        if not hasattr(self, "already_called_update_smb_signal"):
            self.init_smb_signal()
            self.already_called_update_smb_signal = True

        # define ELA as function of EPICA's Delta T, ELA's present day (pdela) and Dela/Dt (deladt)
        ela     = self.config.pdela + self.config.deladt*self.dT(self.t) # for rhine

        # that's SMB param with ELA, ablation and accc gradient, and max accumulation
        # i.e. SMB =       gradabl*(z-ela)           if z<ela, 
        #          =  min( gradacc*(z-ela) , maxacc) if z>ela.
        smb = self.usurf - ela
        smb *= tf.where(tf.less(smb, 0), self.config.gradabl, self.config.gradacc)
        smb = tf.clip_by_value(smb, -100, self.config.maxacc)

        self.smb.assign( smb )

# init IGM
igm = igm()

area = 'ticino' # chose your area among lyon, linth, rhine, ticino
reso = 1000    # chose your resolution among 200,1000, 2000 meters (keep it coarse like 2000 for testing)

igm.config.geology_file            = 'data-for-paleo-tuto/'+area+'-'+str(reso)+'.nc' 
igm.config.tstart                  = -30000 
igm.config.tend                    = -15000
igm.config.tsave                   = 100  # save result each 100 years
igm.config.cfl                     = 0.25 # if you see numerical unstabilities, decrease this.
igm.config.init_strflowctrl        = 100  # this parameter controls the ice flow strengh, if you increase it, you accelerate the ice

# here you can change parameters that parametrize ELA 
igm.config.pdela  = 3000 # Present-day ELA
if area=='rhine':
  igm.config.deladt = 190 
elif area=='linth':
  igm.config.deladt = 220 
else:
  igm.config.deladt = 200

# here you can change parameters that parametrize the mass balance function (as defined above)
igm.config.gradabl = 0.0067   # taken from (Cohen, 2018, TC)
igm.config.gradacc = 0.0005   # taken from (Cohen, 2018, TC)
igm.config.maxacc  = 1.0      # taken from (Cohen, 2018, TC)

if reso<=200:
  igm.config.iceflow_model_lib_path  = '../../model-lib/f12_cfsflow_GJ_21_a' # use this for resolution 100,200
else:
  igm.config.iceflow_model_lib_path  = '../../model-lib/f14_pism_GJ_21_a'    # use this for resolution 1000,2000

igm.config.type_mass_balance       = 'signal'
igm.config.usegpu                  = True

igm.initialize() 
with tf.device(igm.device_name):
    igm.load_ncdf_data(igm.config.geology_file)
    igm.initialize_fields()               
    while igm.t < igm.config.tend:                       
        igm.update_smb()
        igm.update_iceflow()
        igm.update_t_dt() 
        igm.update_thk()       
        igm.update_ncdf_ex()
        igm.update_ncdf_ts()
        igm.update_plot()
        igm.print_info()
        
igm.print_all_comp_info()

igm.animate_result('ex.nc','thk',save=True)

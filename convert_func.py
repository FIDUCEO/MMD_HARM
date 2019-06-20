import numpy as np
from netCDF4 import Dataset

def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx

def dbyd(a1,a2,b1,b2):
    dbyd = ((a2-a1)/(b2-b1))
    return dbyd

##############################################################
#                                                            #
#  FUNCTIONS FOR CONVERTING BETWEEN BT, COUNTS AND RADIANCE  #
#                                                            #  
#  NB: channel=3 --> 3.7 micron                              #
#  NB: channel=4 -->  11 micron                              #
#  NB: channel=5 -->  12 micron                              #
#                                                            #  
#  read_in_LUT()                                             #
#  REQUIRES avhrr_sat to be in the format:                   #
#  N12,N14,N15,N16,N17,N18,N19,MTA,MTB                       #
#  RETURNS LUT dictionary with groups "L" and "BT"           #
#                                                            #
#  rad2bt()                                                  #
#  REQUIRES array of radiance, channel (either 3, 4 or 5)    #
#  and lut output from read_in_LUT (sensor specific)          #
#  RETURNS BT in array of same initial shape of L            # 
#                                                            # 
#  bt2rad()                                                  #
#  REQUIRES array of BT, channel (either 3, 4 or 5)          #
#  and lut output from read_in_LUT (sensor specific)         #
#  RETURNS L in array of same initial shape of BT            #
#                                                            #
#  dbt_drad()                                                #
#  REQUIRES array of radiance, channel (either 3, 4 or 5)    #
#  and lut output from read_in_LUT (sensor specific)         #
#  RETURNS dbt_drad array in the same shape as L input       #
#                                                            #
#  drad_da()                                                 #
#  REQUIRES arrays of Lict,Ce,Cs,Cict,Tict,Tinst,WV          #
#  Also requires channel and satellite sensor.               #
#  RETURNS: If 3.7um channel, then three derivatives of      #
#  radiance with respect to a2,a4,a5 coefficents. Else       #
#  it returns four derivitives of radiance with respect      #
#  to a2,a3,a4 and a5 coefficents                            #
#                                                            #
#  count2rad()                                               #
#  REQUIRES arrays Ce,Cs,Cict,Lict,Tinst,WV,channel (either  #
#  3, 4 or 5), and harmonisation coeffs a1,a2,a3,a4,a5       #
#  RETURNS radiance in array with same shape as Le input     #
#                                                            #
##############################################################

def read_in_LUT(avhrr_sat):
    LUT = {}
    all_lut_radiance_dict = np.load('lut_radiance.npy', encoding='bytes', allow_pickle=True).item()
    all_lut_BT_dict = np.load('lut_BT.npy', encoding='bytes', allow_pickle=True).item()
    try:
        LUT['L'] = all_lut_radiance_dict[avhrr_sat][:]
        LUT['BT'] = all_lut_BT_dict[avhrr_sat][:]
    except:
        print("Sensor for AVHRR does not exist: ", avhrr_sat)
    return LUT

def rad2bt(L,channel,lut):
    BT = np.interp(L,lut['L'][:,channel],lut['BT'][:,channel],left=-999.9,right=-999.9)
    return BT

def bt2rad(BT,channel,lut):
    L = np.interp(BT,lut['BT'][:,channel],lut['L'][:,channel],left=-999.9,right=-999.9)
    return L

def dbt_drad(L,channel,lut):
    dbtdrad = np.zeros_like(L)
    # Over array L, determine the two values in the LUT either side
    # Then, find dbt by drad and add to new array
    for i in xrange(0,len(L)):
        for j in xrange(0,len(L[0])):
            element = L[i,j]
            idx = find_nearest(lut['L'][:,channel],element)
            if lut['L'][idx,channel] > element:
                dbtdrad[i,j] = (dbyd(lut['BT'][idx-1,channel],lut['BT'][idx,channel],lut['L'][idx-1,channel],lut['L'][idx,channel]))
            else:
                dbtdrad[i,j] = (dbyd(lut['BT'][idx,channel],lut['BT'][idx+1,channel],lut['L'][idx,channel],lut['L'][idx+1,channel]))
    return dbtdrad

def drad_da(Lict,Ce,Cs,Cict,Tict,Tinst,WV,channel,avhrr_sat):
    '''
    Added derivative for WV term. It's a dummy array at present. will need replacing by derivative of f(WV)
    '''
    try:
        if channel == 3:
            drad_da2 = Lict/(Cict - Cs)
            drad_da3 = Tinst
            drad_da4 = WV # dummy array at present. will need replacing by derivative of f(WV)
            return drad_da2,drad_da3,drad_da4
        elif channel > 3:
            drad_da2 = Lict/(Cict - Cs)
            drad_da3 = (Ce - Cict) * (Ce - Cs)
            drad_da4 = Tinst
            drad_da5 = WV # dummy array at present. will need replacing by derivative of f(WV)
            return drad_da2,drad_da3,drad_da4,drad_da5

    except:
        print("No FIDUCEO thermal channel selected: channel=", channel, " < 3")
    
def count2rad(Ce,Cs,Cict,Lict,Tstar,WV,channel,a0,a1,a2,a3,a4,noT):
    '''
    NB: Tstar = (T_inst - T_mean) / T_std
    NB: WV is a dummy term currently unused
    NB: MTA is a boolean flag: if True --> #105 and #101 (if False --> #106 and #102)
    '''
    L = np.empty(shape=(Ce.shape[0],Ce.shape[1]))
    try:
        if channel == 3:
            if noT:
                L = a0 + ((Lict * (0.985140 + a1)) / (Cict - Cs)) * (Ce - Cs)                             # 105
            L = a0 + ((Lict * (0.985140 + a1)) / (Cict - Cs)) * (Ce - Cs) + a2 * Tstar                    # 106
        elif channel > 3:  
            if noT:
                L = a0 + ((Lict * (0.985140 + a1)) / (Cict - Cs) + a2 * (Ce - Cict)) * (Ce - Cs)          # 101
            L = a0 + ((Lict * (0.985140 + a1)) / (Cict - Cs) + a2 * (Ce - Cict)) * (Ce - Cs) + a3 * Tstar # 102
    except:
        print("No FIDUCEO thermal channel selected: channel=", channel, " < 3")

    return L


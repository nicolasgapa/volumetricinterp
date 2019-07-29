# test_fit.py
# tests evaluating coefficients from volumetric interpolation

import numpy as np
import datetime as dt
from amisr_fit import EvalParam
import coord_convert as cc

# set input coordinates
lat, lon = np.meshgrid(np.linspace(75., 80.,10), np.linspace(260., 280.,10))
alt = np.full(lat.shape, 300.)
r, t, p = cc.geodetic_to_spherical(lat, lon, alt)
R0 = np.array([r,t,p])

time = dt.datetime(2017,11,19,0,5,3)

param = EvalParam('test_out.h5')
dens = param.getparam(time,R0)
print(dens)
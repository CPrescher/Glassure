# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import numpy as np

q= np.linspace(0,20, 10)
r = np.linspace(0,12,12)

fr = np.linspace(0,12,12)

res = np.mat(np.sin(np.mat(q).T*np.mat(r)))*np.mat(fr).T

print res
print res.shape

res1 = np.trapz(res,r)

print res1.shape
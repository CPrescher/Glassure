"""
Converts the incoherent scattering data from the individual files to a single csv file. Also converts the s values to Q
values.
"""
import os
import numpy as np
import pandas as pd

files = os.listdir('incoherent')

result = pd.DataFrame()
# hubbell data is saved in s --> Q = 4 * pi * s
result['q'] = np.loadtxt(os.path.join('incoherent', 'Ac.dat'), skiprows=1)[:, 0] * np.pi * 4

for file in files:
    name, ext = os.path.splitext(file)
    if ext == '.dat':
        data = np.loadtxt(os.path.join('incoherent', file), skiprows=1)
        result[name] = data[:, 2]

result.to_csv('incoherent_scattering_intensities.csv', index=False)

__author__ = 'Clemens Prescher'

import os
import numpy as np
import pandas
from . import _module_path

module_data_path = os.path.join(_module_path(), 'data')

scattering_factor_param = pandas.read_csv(os.path.join(module_data_path, 'param_atomic_scattering_factors.csv'),
                                          index_col=0)

scattering_intensity_param = pandas.read_csv(
    os.path.join(module_data_path, 'param_incoherent_scattering_intensities.csv'),
    index_col=0)

atomic_weights = pandas.read_csv(os.path.join(
    module_data_path, 'atomic_weights.csv'),
                                 index_col=0)


def calculate_coherent_scattering_factor(element, q):
    if not element in scattering_factor_param.index.values:
        raise ElementNotImplementedException(element)
    fs_coh = 0
    s = q / (4 * np.pi)
    for ind in xrange(1, 5):
        A = scattering_factor_param['A' + str(ind)][element]
        B = scattering_factor_param['B' + str(ind)][element]
        fs_coh += A * np.exp(-B * s ** 2)

    C = scattering_factor_param['C'][element]
    fs_coh += C
    return fs_coh


def calculate_incoherent_scattered_intensity(element, q):
    fs_coherent = calculate_coherent_scattering_factor(element, q)
    intensity_coherent = fs_coherent ** 2
    s = q / (4 * np.pi)
    Z = np.float(scattering_intensity_param['Z'][element])
    M = np.float(scattering_intensity_param['M'][element])
    K = np.float(scattering_intensity_param['K'][element])
    L = np.float(scattering_intensity_param['L'][element])
    intensity_incoherent = (Z - intensity_coherent / Z) * (1 - M * (np.exp(-K * s) - np.exp(-L * s)))
    return intensity_incoherent


class ElementNotImplementedException(Exception):
    def __init__(self, element):
        self.element = element

    def __str__(self):
        return repr('Element ' + self.element + ' not known or available.')

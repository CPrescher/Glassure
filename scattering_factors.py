__author__ = 'doomgoroth'

import numpy as np
import pandas
import matplotlib.pyplot as plt

scattering_factor_param = pandas.read_csv('data/param_atomic_scattering_factors.csv', index_col=0)
scattering_intensity_param = pandas.read_csv('data/param_incoherent_scattering_intensities.csv', index_col=0)

print scattering_intensity_param['K']['Ca']

print scattering_factor_param.index.values

def calculate_coherent_scattering_factor(element, q):
    if not element in scattering_factor_param.index.values:
        raise ElementNotImplementedException(element)
    fs_coh = 0
    s=q/(4*np.pi)
    for ind in xrange(1,5):
        A = scattering_factor_param['A'+str(ind)][element]
        B = scattering_factor_param['B'+str(ind)][element]
        fs_coh+=A*np.exp(-B*s**2)

    C = scattering_factor_param['C'][element]
    fs_coh+=C
    return fs_coh

def calculate_incoherent_scattering_factor(element, q):
    fs_coh = calculate_coherent_scattering_factor(element, q)
    s=q/(4*np.pi)
    Z = np.float(scattering_intensity_param['Z'][element])
    M = np.float(scattering_intensity_param['M'][element])
    K = np.float(scattering_intensity_param['K'][element])
    L = np.float(scattering_intensity_param['L'][element])
    fs_incoh = (Z-fs_coh/Z)*(1-M*np.exp(-K*s)-np.exp(-L*s))
    return fs_incoh

class ElementNotImplementedException(Exception):
    def __init__(self, element):
        self.element = element
    def __str__(self):
        return repr('Element '+self.element+' not known or available.')

if __name__ == '__main__':
    q = np.linspace(0,30,1600)
    fs_coh = calculate_incoherent_scattering_factor('He',q)
    plt.plot(q, fs_coh, label = 'He')
    fs_coh = calculate_incoherent_scattering_factor('Ca',q)
    plt.plot(q, fs_coh, label = 'Ca')
    fs_coh = calculate_incoherent_scattering_factor('Na',q)
    plt.plot(q, fs_coh, label = 'Na')
    fs_coh = calculate_incoherent_scattering_factor('Mg',q)
    plt.plot(q, fs_coh, label = 'Mg')
    fs_coh = calculate_incoherent_scattering_factor('Fe',q)
    plt.plot(q, fs_coh, label = 'Fe')
    plt.legend()
    plt.show()
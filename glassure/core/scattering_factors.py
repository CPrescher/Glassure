# -*- coding: utf-8 -*-

import os
import numpy as np
import scipy
import pandas
from . import _module_path

module_data_path = os.path.join(_module_path(), 'data')

atomic_weights = pandas.read_csv(os.path.join(
    module_data_path, 'atomic_weights.csv'),
    index_col=0)


class ScatteringFactorCalculator:
    """
    Abstract class for scattering factor calculators.
    """

    def get_coherent_scattering_factor(self, element: str, q):
        raise NotImplementedError

    def get_incoherent_intensity(self, element: str, q):
        raise NotImplementedError

    @property
    def elements(self):
        raise NotImplementedError


class ScatteringFactorCalculatorHajdu(ScatteringFactorCalculator):
    """
    Scattering factor calculator based on the work of Hajdu et al. (Acta Cryst. (1992). A48, 344-352).
    """

    def __init__(self):
        self.coherent_param = pandas.read_csv(
            os.path.join(module_data_path, 'hajdu', 'param_coherent_scattering_factors.csv'),
            index_col=0)
        self.incoherent_param = pandas.read_csv(
            os.path.join(module_data_path, 'hajdu', 'param_incoherent_scattering_intensities.csv'),
            index_col=0)

    def get_coherent_scattering_factor(self, element: str, q):
        """
        Calculates the coherent scattering factor for a given element and q values.
        :param element: Element symbol
        :param q: q array
        :return: coherent scattering factor array
        """
        if element not in self.coherent_param.index.values:
            raise ElementNotImplementedException(element)
        fs_coh = 0
        s = q / (4 * np.pi)
        for ind in range(1, 5):
            A = self.coherent_param['A' + str(ind)][element]
            B = self.coherent_param['B' + str(ind)][element]
            fs_coh += A * np.exp(-B * s ** 2)

        C = self.coherent_param['C'][element]
        fs_coh += C
        return fs_coh

    def get_incoherent_intensity(self, element: str, q):
        """
        Calculates the incoherent scattering intensity for a given element and q values.
        :param element: Element symbol
        :param q: q array
        :return: incoherent scattering intensity array
        """
        fs_coherent = self.get_coherent_scattering_factor(element, q)
        intensity_coherent = fs_coherent ** 2
        s = q / (4 * np.pi)
        Z = float(self.incoherent_param['Z'][element])
        M = float(self.incoherent_param['M'][element])
        K = float(self.incoherent_param['K'][element])
        L = float(self.incoherent_param['L'][element])
        intensity_incoherent = (Z - intensity_coherent / Z) * (1 - M * (np.exp(-K * s) - np.exp(-L * s)))
        return intensity_incoherent

    @property
    def elements(self):
        return self.coherent_param.index.values


class ScatteringFactorCalculatorBrownHubbell(ScatteringFactorCalculator):
    """
    Scattering factor calculator based on the work of Brown et al., 2006 and Hubbell et al., 1975.
    """

    def __init__(self):
        self.coherent_params = pandas.read_csv(
            os.path.join(module_data_path, 'brown_hubbell', 'param_coherent_scattering_factors.csv'),
            index_col=0)

        self.incoherent_intensities = pandas.read_csv(
            os.path.join(module_data_path, 'brown_hubbell', 'incoherent_scattering_intensities.csv'))

    def get_coherent_scattering_factor(self, element: str, q):
        """
        Calculates the coherent scattering factor for a given element and q values.
        :param element: Element symbol
        :param q: q array
        :return: coherent scattering factor array
        """
        if element not in self.coherent_params.index.values:
            raise ElementNotImplementedException(element)
        fs_coh = 0
        s = q / (4 * np.pi)
        for ind in range(1, 5):
            A = self.coherent_params['a' + str(ind)][element]
            B = self.coherent_params['b' + str(ind)][element]
            fs_coh += A * np.exp(-B * s ** 2)

        C = self.coherent_params['c'][element]
        fs_coh += C
        return fs_coh

    def get_incoherent_intensity(self, element: str, q):
        """
        Calculates the incoherent scattering intensity for a given element and q values.
        :param element: Element symbol
        :param q: q array
        :return: incoherent scattering intensity array
        """
        if element not in self.incoherent_intensities.keys():
            raise ElementNotImplementedException(element)
        interp = scipy.interpolate.interp1d(self.incoherent_intensities['q'], self.incoherent_intensities[element],
                                            kind='cubic')
        return interp(q)

    @property
    def elements(self):
        return self.incoherent_intensities.keys()


scattering_calculator = ScatteringFactorCalculatorHajdu()


def calculate_coherent_scattering_factor(element, q):
    return scattering_calculator.get_coherent_scattering_factor(element, q)


def calculate_incoherent_scattered_intensity(element, q):
    return scattering_calculator.get_incoherent_intensity(element, q)


class ElementNotImplementedException(Exception):
    def __init__(self, element):
        self.element = element

    def __str__(self):
        return repr('Element ' + self.element + ' not known or available.')

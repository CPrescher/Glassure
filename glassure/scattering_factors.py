# -*- coding: utf-8 -*-
import os
import re
from abc import ABC, abstractmethod

import numpy as np
import scipy
from scipy.interpolate import interp1d
import pandas
from . import _module_path

import xraylib as xr

module_data_path = os.path.join(_module_path(), "data")

atomic_weights = pandas.read_csv(
    os.path.join(module_data_path, "atomic_weights.csv"), index_col=0
)


class ScatteringFactorCalculator(ABC):
    """
    Abstract class for scattering factor calculators.
    """

    @abstractmethod
    def get_coherent_scattering_factor(self, element: str, q):
        raise NotImplementedError

    @abstractmethod
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
            os.path.join(
                module_data_path, "hajdu", "param_coherent_scattering_factors.csv"
            ),
            index_col=0,
        )
        self.incoherent_param = pandas.read_csv(
            os.path.join(
                module_data_path, "hajdu", "param_incoherent_scattering_intensities.csv"
            ),
            index_col=0,
        )

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
            A = self.coherent_param.loc[element, "A" + str(ind)]
            B = self.coherent_param.loc[element, "B" + str(ind)]
            fs_coh += A * np.exp(-B * s**2)

        C = self.coherent_param.loc[element, "C"]
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
        intensity_coherent = fs_coherent**2
        s = q / (4 * np.pi)
        Z = float(self.incoherent_param.loc[element, "Z"])
        M = float(self.incoherent_param.loc[element, "M"])
        K = float(self.incoherent_param.loc[element, "K"])
        L = float(self.incoherent_param.loc[element, "L"])
        intensity_incoherent = (Z - intensity_coherent / Z) * (
            1 - M * (np.exp(-K * s) - np.exp(-L * s))
        )
        return intensity_incoherent

    @property
    def elements(self):
        """
        Returns a list of available elements.
        """
        return self.coherent_param.index.values


class ScatteringFactorCalculatorBrownHubbell(ScatteringFactorCalculator):
    """
    Scattering factor calculator based on the work of Brown et al., 2006 and Hubbell et al., 1975.
    """

    def __init__(self):
        self.coherent_params = pandas.read_csv(
            os.path.join(
                module_data_path,
                "brown_hubbell",
                "param_coherent_scattering_factors.csv",
            ),
            index_col=0,
        )

        self.incoherent_intensities = pandas.read_csv(
            os.path.join(
                module_data_path,
                "brown_hubbell",
                "incoherent_scattering_intensities.csv",
            )
        )

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
            A = self.coherent_params.loc[element, "a" + str(ind)]
            B = self.coherent_params.loc[element, "b" + str(ind)]
            fs_coh += A * np.exp(-B * s**2)

        C = self.coherent_params.loc[element, "c"]
        fs_coh += C
        return fs_coh

    def get_incoherent_intensity(self, element: str, q):
        """
        Calculates the incoherent scattering intensity for a given element and q values.

        :param element: Element symbol
        :param q: q array
        :return: incoherent scattering intensity array
        """
        # use regular expression to find element string of input
        element = re.findall("[A-zA-Z]*", element)[0]
        if element not in self.incoherent_intensities.keys():
            raise ElementNotImplementedException(element)
        interp = scipy.interpolate.interp1d(
            self.incoherent_intensities["q"],
            self.incoherent_intensities[element],
            kind="cubic",
        )
        return interp(q)

    @property
    def elements(self):
        """
        Returns a list of available elements.
        """
        return self.coherent_params.index.values


class ScatteringFactorCalculatorXraylib(ScatteringFactorCalculator):
    """
    Scattering factor calculator using xraylib library. See https://github.com/tschoonj/xraylib/wiki
    for more details.
    """

    def __init__(self):
        """
        Initializes the xraylib scattering factor calculator.
        """

        self._elements = [xr.AtomicNumberToSymbol(i) for i in range(1, 108)]

    def get_coherent_scattering_factor(self, element: str, q):
        """
        Calculates the coherent scattering factor for a given element and q values.

        :param element: Element symbol
        :param q: q array
        :return: coherent scattering factor array
        """
        q_xr = q / (4 * np.pi)
        element_number = xr.SymbolToAtomicNumber(element)
        return np.array([xr.FF_Rayl(element_number, v) for v in q_xr])

    def get_incoherent_intensity(self, element: str, q):
        """
        Calculates the incoherent scattering intensity for a given element and q values,
        using SF_Compt for q_xr >= 0.001, and cubic interpolation for q_xr < 0.001.

        :param element: Element symbol
        :param q: 1D numpy array of q values
        :return: numpy array of incoherent scattering intensity
        """
        element_number = xr.SymbolToAtomicNumber(element)
        q_xr = q / (4 * np.pi)

        # Split into high and low q_xr regions
        low_mask = q_xr < 0.001
        high_mask = ~low_mask

        # Initialize result array
        values = np.zeros_like(q_xr)

        # Compute SF_Compt for q_xr >= 0.001
        q_xr_high = q_xr[high_mask]
        sf_high = np.array([xr.SF_Compt(element_number, v) for v in q_xr_high])
        values[high_mask] = sf_high

        # Interpolate for q_xr < 0.001
        if np.any(low_mask) and q_xr_high.size >= 4:  # at least 4 points for cubic
            n_interp = min(3, q_xr_high.size)
            left_interp_x = np.arange(0, -1, -(q_xr[1] - q_xr[0]))
            left_interp_y = np.zeros_like(left_interp_x)
            interp_q = np.concatenate((left_interp_x, q_xr_high[:n_interp]))
            interp_sf = np.concatenate((left_interp_y, sf_high[:n_interp]))

            f_interp = interp1d(
                interp_q, interp_sf, kind="cubic", bounds_error=False, fill_value=0.0
            )

            values[low_mask] = f_interp(q_xr[low_mask])
        else:
            # If not enough points for interpolation, set to zero
            values[low_mask] = 0.0

        return values

    @property
    def elements(self):
        """
        Returns a list of available elements.
        """
        return self._elements


calculators = {
    "hajdu": ScatteringFactorCalculatorHajdu(),
    "brown_hubbell": ScatteringFactorCalculatorBrownHubbell(),
    "xraylib": ScatteringFactorCalculatorXraylib(),
}

sources = calculators.keys()


def get_calculator(source: str) -> ScatteringFactorCalculator:
    """
    Returns the calculator for a given source. Possible sources are 'hajdu', 'brown_hubbell' and 'xraylib'.
    """
    if source not in calculators.keys():
        raise SourceNotImplementedException(source)
    return calculators[source]


def get_available_elements(source: str) -> list[str]:
    """
    Returns a list of available elements for a given source. Possible sources are 'hajdu', 'brown_hubbell' and
    'xraylib'.
    """
    return get_calculator(source).elements


def calculate_coherent_scattering_factor(
    element: str, q: np.ndarray, source: str = "hajdu"
) -> np.ndarray:
    """
    Calculates the coherent scattering factor for a given element and q values.

    :param element: Element symbol
    :param q: q array in A^-1
    :param source: Source of the scattering factors. Possible sources are 'hajdu', 'brown_hubbell' and 'xraylib'.
    :return: coherent scattering factor array
    """
    return get_calculator(source).get_coherent_scattering_factor(element, q)


def calculate_incoherent_scattered_intensity(
    element: str, q: np.ndarray, source: str = "hajdu"
) -> np.ndarray:
    """
    Calculates the incoherent scattering intensity for a given element and q values.

    :param element: Element symbol
    :param q: q array
    :param source: Source of the scattering factors. Possible sources are 'hajdu', 'brown_hubbell' and 'xraylib'.
    :return: incoherent scattering intensity array
    """
    return get_calculator(source).get_incoherent_intensity(element, q)


class ElementNotImplementedException(Exception):
    def __init__(self, element):
        self.element = element

    def __str__(self):
        return repr("Element " + self.element + " not known or available.")


class SourceNotImplementedException(Exception):
    def __init__(self, source):
        self.source = source

    def __str__(self):
        return repr("Source " + self.source + " not known or available.")

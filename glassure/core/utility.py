# -*- coding: utf-8 -*-
import re
from copy import copy

import numpy as np
from scipy import interpolate
import lmfit

from .scattering_factors import calculate_coherent_scattering_factor, calculate_incoherent_scattered_intensity
from . import Pattern
from . import scattering_factors

__all__ = ['calculate_f_mean_squared', 'calculate_f_squared_mean', 'calculate_incoherent_scattering',
           'extrapolate_to_zero_linear', 'extrapolate_to_zero_poly', 'extrapolate_to_zero_spline',
           'extrapolate_to_zero_step', 'convert_density_to_atoms_per_cubic_angstrom', 'normalize_composition',
           'convert_two_theta_to_q_space', 'convert_two_theta_to_q_space_raw', 'calculate_weighting_factor']


def calculate_f_mean_squared(composition: dict, q: np.ndarray, sf_source='hajdu') -> np.ndarray:
    """
    Calculates the square of the mean form_factor for a given composition over q.
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for element, amount in norm_elemental_abundances.items():
        res += amount * calculate_coherent_scattering_factor(element, q, sf_source)
    return res ** 2


def calculate_f_squared_mean(composition: dict[str, float], q: np.ndarray, sf_source: str = 'hajdu') -> np.ndarray:
    """
    Calculates the mean of the squared form factors for a given composition for a given q vector.
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: mean of the squared form factors
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_coherent_scattering_factor(key, q, sf_source) ** 2
    return res


def calculate_incoherent_scattering(composition: dict[str, float], q: np.ndarray, sf_source: str = 'hajdu') \
        -> np.ndarray:
    """
    Calculates compton/incoherent scattering for a given composition
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: incoherent scattering array
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_incoherent_scattered_intensity(key, q, sf_source)
    return res


def calculate_weighting_factor(composition: dict[str, float], element_1: str, element_2: str, q: np.ndarray,
                               sf_source='hajdu'):
    """
    Calculates the weighting factor for an element-element contribution in a given composition (e.g. for Si-O in SiO2)
    :param composition: dictionary with elements as key string and abundances as relative numbers
    :param element_1: string giving element 1
    :param element_2: string giving element 2
    :param q: Q value or numpy array with a unit of A^-1
    :param sf_source: source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: weighting factor array
    """
    if element_1 == element_2:
        factor = 1
    else:
        factor = 2

    num_atoms = sum([val for _, val in composition.items()])
    f = {}  # form factors
    c = {}  # concentrations
    for element, val in composition.items():
        f[element] = calculate_coherent_scattering_factor(element, q, sf_source)
        c[element] = val / num_atoms

    f_sum_squared = np.zeros_like(q)
    for element, conc in c.items():
        f_sum_squared += f[element] * conc
    f_sum_squared = f_sum_squared ** 2

    return factor * c[element_1] * c[element_2] * f[element_1] * f[element_2] / f_sum_squared


def normalize_composition(composition):
    """
    normalizes elemental abundances to 1
    :param composition: dictionary with elements as key and abundances as relative numbers
    :return: normalized elemental abundances dictionary
    """
    sum = 0.0
    for key, val in composition.items():
        sum += val

    result = copy(composition)

    for key in result:
        result[key] /= sum

    return result


def convert_density_to_atoms_per_cubic_angstrom(composition, density):
    """
    Converts densities given in g/cm3 into atoms per A^3
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param density: density in g/cm^3
    :return: density in atoms/A^3
    """

    # get_smallest abundance
    norm_elemental_abundances = normalize_composition(composition)
    mean_z = 0.0
    for element, concentration in norm_elemental_abundances.items():
        element = re.findall('[A-zA-Z]*', element)[0]
        mean_z += concentration * scattering_factors.atomic_weights['AW'][element]
    return density / mean_z * .602214129


def extrapolate_to_zero_step(pattern):
    """
    Extrapolates a pattern to (0, 0) by setting everything below the q_min of the pattern to zero
    :param pattern: input Pattern
    :return: extrapolated Pattern
    """
    x, y = pattern.data
    step = x[1] - x[0]
    low_x = np.sort(np.arange(min(x), 0, -step))
    low_y = np.zeros(low_x.shape)

    return Pattern(np.concatenate((low_x, x)),
                   np.concatenate((low_y, y)))


def extrapolate_to_zero_linear(pattern):
    """
    Extrapolates a pattern to (0, 0) using a linear function from the most left point in the pattern
    :param pattern: input Pattern
    :return: extrapolated Pattern (includes the original one)
    """
    x, y = pattern.data
    step = x[1] - x[0]
    low_x = np.sort(np.arange(min(x), 0, -step))
    low_y = y[0] / x[0] * low_x
    return Pattern(np.concatenate((low_x, x)),
                   np.concatenate((low_y, y)))


def extrapolate_to_zero_spline(pattern, x_max, smooth_factor=None, replace=False):
    """
    Extrapolates a pattern to (0, 0) using a spline function.
    If the spline hits zero on the y-axis at an x value higher than 0 all values below this intersection
    will be set to zero

    :param pattern: input pattern
    :param x_max: defines the the maximum x value within the spline will be fitted to the input pattern, This parameter
    should be larger than minimum of the pattern x
    :param smooth_factor: defines the smoothing of the spline extrapolation please see numpy.UnivariateSpline manual for
    explanations
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :return: extrapolated Pattern (includes the original one)
    """

    x, y = pattern.data
    x_step = x[1] - x[0]
    x_low = np.sort(np.arange(min(x), 0, -x_step))

    x_inter = np.concatenate(([0], x[x < x_max]))
    y_inter = np.concatenate(([0], y[x < x_max]))

    if replace:
        x_low = np.concatenate((x_low, x_inter[1:]))
        ind = x > x_max
        x = x[ind]
        y = y[ind]

    spl = interpolate.UnivariateSpline(x_inter, y_inter, s=smooth_factor)
    y_low = spl(x_low)

    ind_below_zero = np.where(y_low < 0)[0]

    if len(ind_below_zero) > 0:
        y_low[:ind_below_zero[-1]] = 0

    return Pattern(np.concatenate((x_low, x)),
                   np.concatenate((y_low, y)))


def extrapolate_to_zero_poly(pattern, x_max, replace=False):
    """
    Extrapolates a pattern to (0, 0) using a 2nd order polynomial:

    a*(x-c)+b*(x-c)^2

    :param pattern: input pattern
    :param x_max: defines the maximum x value within the polynomial will be fit
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :return: extrapolated Pattern
    """

    x, y = pattern.data
    x_step = x[1] - x[0]

    x_fit = x[x < x_max]
    y_fit = y[x < x_max]

    params = lmfit.Parameters()
    params.add("a", value=1, min=0)
    params.add("b", value=1, min=0)
    params.add("c", value=1)

    def optimization_fcn(params):
        a = params['a'].value
        b = params['b'].value
        c = params['c'].value

        return (y_fit - (x_fit - c) * a - (x_fit - c) ** 2 * b)

    result = lmfit.minimize(optimization_fcn, params)
    a = result.params['a'].value
    b = result.params['b'].value
    c = result.params['c'].value

    x_low = np.sort(np.arange(min(x), 0, -x_step))
    if replace:
        x_low = np.concatenate((x_low, x_fit[1:]))
        ind = x > x_max
        x = x[ind]
        y = y[ind]
    y_low = a * (x_low - c) + b * (x_low - c) ** 2
    y_low[x_low < c] = 0

    return Pattern(np.concatenate((x_low, x)),
                   np.concatenate((y_low, y)))


def convert_two_theta_to_q_space_raw(two_theta, wavelength):
    """
    Converts two theta values into q space
    """
    return 4 * np.pi * np.sin(two_theta / 360.0 * np.pi) / wavelength


def convert_two_theta_to_q_space(pattern, wavelength):
    """
    Returns a new pattern with the x-axis converted from two theta into q space
    """
    q_pattern = copy(pattern)
    q_pattern._x = convert_two_theta_to_q_space_raw(q_pattern.x, wavelength)
    return q_pattern

# -*- coding: utf8 -*-

from copy import copy

import numpy as np
from scipy import interpolate
import lmfit

from .scattering_factors import calculate_coherent_scattering_factor, calculate_incoherent_scattered_intensity
from . import Pattern
from . import scattering_factors

__all__ = ['calculate_f_mean_squared', 'calculate_f_squared_mean', 'calculate_incoherent_scattering',
           'extrapolate_to_zero_linear', 'extrapolate_to_zero_poly', 'extrapolate_to_zero_spline',
           'convert_density_to_atoms_per_cubic_angstrom',
           'convert_two_theta_to_q_space', 'convert_two_theta_to_q_space_raw']


def calculate_f_mean_squared(composition, q):
    """
    Calculates the square of the mean form_factor for a given composition over q.
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_coherent_scattering_factor(key, q)
    return res ** 2


def calculate_f_squared_mean(composition, q):
    """
    Calculates the mean of the squared form factors for a given composition for a given q vector.
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_coherent_scattering_factor(key, q) ** 2
    return res


def calculate_incoherent_scattering(composition, q):
    """
    Calculates compton/incoherent scattering for a given composition
    :param composition: dictionary with elements as key and abundances as relative numbers
    :param q: Q value or numpy array with a unit of A^-1
    """
    norm_elemental_abundances = normalize_composition(composition)

    res = 0
    for key, value in norm_elemental_abundances.items():
        res += value * calculate_incoherent_scattered_intensity(key, q)
    return res


def normalize_composition(composition):
    """
    normalizes elemental abundances to 1
    :param composition: dictionary with elements as key and abundances as relative numbers
    :return: normalized elemental abundances dictionary dictionary
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
    for key, val in norm_elemental_abundances.items():
        mean_z += val * scattering_factors.atomic_weights['AW'][key]
    return density / mean_z * .602214129


def extrapolate_to_zero_step(spectrum):
    """
    Extrapolates a spectrum to (0, 0) by setting everything below the q_min of the spectrum to zero
    :param spectrum: input Spectrum
    :return: extrapolated Spectrum
    """
    x, y = spectrum.data
    step = x[1] - x[0]
    low_x = np.sort(np.arange(min(x), 0, -step))
    low_y = np.zeros(low_x.shape)

    return Pattern(np.concatenate((low_x, x)),
                   np.concatenate((low_y, y)))


def extrapolate_to_zero_linear(spectrum):
    """
    Extrapolates a spectrum to (0, 0) using a linear function from the most left point in the spectrum
    :param spectrum: input Spectrum
    :return: extrapolated Spectrum (includes the original one)
    """
    x, y = spectrum.data
    step = x[1] - x[0]
    low_x = np.sort(np.arange(min(x), 0, -step))
    low_y = y[0] / x[0] * low_x
    return Pattern(np.concatenate((low_x, x)),
                   np.concatenate((low_y, y)))


def extrapolate_to_zero_spline(spectrum, x_max, smooth_factor=None, replace=False):
    """
    Extrapolates a spectrum to (0, 0) using a spline function.
    If the spline hits zero on the y-axis at an x value higher than 0 all values below this intersection
    will be set to zero

    :param spectrum: input spectrum
    :param x_max: defines the the maximum x value within the spline will be fitted to the input spectrum, This parameter
    should be larger than minimum of the spectrum x
    :param smooth_factor: defines the smoothing of the spline extrapolation please see numpy.UnivariateSpline manual for
    explanations
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :return: extrapolated Spectrum (includes the original one)
    """

    x, y = spectrum.data
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


def extrapolate_to_zero_poly(spectrum, x_max, replace=False):
    """
    Extrapolates a spectrum to (0, 0) using a 2nd order polynomial:

    a*(x-c)+b*(x-c)^2

    :param spectrum: input spectrum
    :param x_max: defines the maximum x value within the polynomial will be fit
    :param replace: boolean flag whether to replace the data values in the fitted region (default = False)
    :return: extrapolated Spectrum
    """

    x, y = spectrum.data
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


def convert_two_theta_to_q_space(spectrum, wavelength):
    """
    Returns a new spectrum with the x-axis converted from two theta into q space
    """
    q_spectrum = copy(spectrum)
    q_spectrum._x = convert_two_theta_to_q_space_raw(q_spectrum.x, wavelength)
    return q_spectrum

# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
from copy import copy
import numpy as np
from lmfit import minimize, Parameters, fit_report

from ScatteringFactors import calculate_coherent_scattering_factor, calculate_incoherent_scattered_intensity
import ScatteringFactors

from Spectrum import Spectrum


def optimize_r_cutoff(data_spectrum, bkg_spectrum,
                      initial_background_scaling, elemental_abundances,
                      initial_density, r_cutoff,
                      callback_fcn=None):
    def optimization_fcn(pars):
        parvals = pars.valuesdict()
        r_cutoff = parvals['r_cutoff']

        _, _, _, density_err = optimize_background_scaling_and_density(data_spectrum, bkg_spectrum,
                                                                       initial_background_scaling, elemental_abundances,
                                                                       initial_density, r_cutoff)

        return [abs(density_err)]

    pars = Parameters()
    pars.add('r_cutoff', r_cutoff)

    minimize(optimization_fcn, pars)

    return pars['r_cutoff'].value


def optimize_background_scaling_and_density(data_spectrum, bkg_spectrum,
                                            initial_background_scaling, elemental_abundances,
                                            initial_density, r_cutoff,
                                            callback_fcn=None):
    """
    Uses optimization algorithm defined in Eggert et al. 2002 for determination of best background_scaling and density

    :param data_spectrum: originally collected data_spectrum
    :param bkg_spectrum: originally collected bkg_spectrum
    :param initial_background_scaling: start_value for the background scaling
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :param initial_density: starting value for the density
    :param r_cutoff: maximum r for which the optimization takes place
    :param callback_fcn: a function which will be called every iteration, function should have 5 parameters:
         background_scaling, density
    :return: optimized background_scaling, optimized density
    """

    r = np.linspace(0, r_cutoff, 100)

    def optimization_fcn(parameters):
        parvals = pars.valuesdict()
        background_scaling = parvals['background_scaling']
        density = parvals['density']
        sq_spectrum = calc_sq(data_spectrum, bkg_spectrum, background_scaling, elemental_abundances, density)
        fr_spectrum = calc_fr_from_sq_matrix(sq_spectrum, r)
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density)

        fr_x, fr_y = fr_spectrum.data
        chi2 = (-fr_y - 4 * np.pi * atomic_density) ** 2
        return chi2

    pars = Parameters()
    pars.add('background_scaling', initial_background_scaling, min=0, max=10)
    pars.add('density', initial_density, min=0)

    minimize(optimization_fcn, pars)
    print fit_report(pars)

    return pars['background_scaling'].value, pars['background_scaling'].stderr, \
           pars['density'].value, pars['density'].stderr


def calc_transforms(data_spectrum, bkg_spectrum, background_scaling, elemental_abundances, density, r):
    sq_spectrum = calc_sq(data_spectrum, bkg_spectrum, background_scaling, elemental_abundances, density)
    fr_spectrum = calc_fr_from_sq_matrix(sq_spectrum, r)
    gr_spectrum = calc_gr_from_fr(fr_spectrum, elemental_abundances, density)

    return sq_spectrum, fr_spectrum, gr_spectrum

def calc_gr_from_fr(fr_spectrum, elemental_abundances, density):
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density)
    r, f_r = fr_spectrum.data
    g_r = f_r / (4.0 * np.pi * r) + atomic_density
    return Spectrum(r, g_r/atomic_density)


def calc_fr_from_sq(sq_spectrum, r):
    """
    Calculates F(r) from the structure factor S(q). Uses iteration to calculate each integral.
    :param sq_spectrum: Structure factor Spectrum
    :param r: array of r values in Angstrom
    :return: F(r) spectrum
    """
    q, intensity = sq_spectrum.data
    integral = np.zeros(r.shape)
    for ind, val in enumerate(r):
        integral[ind] = np.trapz(q * (intensity - 1) * np.sin(q * val), q)
    fr = 2.0 / np.pi * integral
    return Spectrum(r, fr)


def calc_fr_from_sq_matrix(sq_spectrum, r):
    """
    Calculates F(r) from the structure factor S(q). Uses 
    :param sq_spectrum: Structure factor Spectrum
    :param r: array of r values in Angstrom
    :return: F(r) spectrum
    """

    q, intensity = sq_spectrum.data
    q_begin = np.arange(0, np.min(q), q[1]-q[0])
    intensity_begin = np.zeros(q_begin.shape)

    q = np.concatenate((q_begin, q))
    intensity = np.concatenate((intensity_begin, intensity))

    fr = 2.0 / np.pi * np.trapz(q * (intensity - 1) *
                                np.array(np.sin(np.mat(q).T * np.mat(r))).T, q)

    return Spectrum(r, fr)


def calc_sq(data_spectrum, background_spectrum, background_scaling, elemental_abundances, density):
    """
    Calculates the structure factor
    :param data_spectrum: originally collected spectrum (maybe smoothed etc.)
    :param background_spectrum: background spectrum
    :param background_scaling: scaling for the background_spectrum
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :param density: density in g/cm^3
    :return:
    """

    sample_spectrum = data_spectrum - background_scaling * background_spectrum
    alpha = calculate_normalization_factor(elemental_abundances, density, sample_spectrum)
    q, int = sample_spectrum.data
    structure_factor = (alpha * int - calculate_incoherent_scattering(elemental_abundances, q)) / \
                       calculate_f_mean_squared(elemental_abundances, q)

    return Spectrum(q, structure_factor)


def calculate_normalization_factor(elemental_abundances, density, spectrum):
    """
    calculates the normalization factor for a spectrum based on elemental abundances and density
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :param density: density in g/cm**3
    :param spectrum: spectrum object (with x and y values)
    :return: float - normalization factor
    """
    q, intensity = spectrum.data

    # obtaining required derived values from scattering factors
    f_mean_squared = calculate_f_mean_squared(elemental_abundances, q)
    incoherent_scattering = calculate_incoherent_scattering(elemental_abundances, q)
    f_squared_mean = calculate_f_squared_mean(elemental_abundances, q)

    # calculate values for integrals
    n1 = q ** 2 * ((f_squared_mean + incoherent_scattering) * np.exp(-0.01 * q ** 2)) / f_mean_squared
    n2 = q ** 2 * intensity * np.exp(-0.01 * q ** 2) / f_mean_squared

    # recalculate density in atomic units

    density_au = convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density)

    # calculate atomic scattering factor
    n = ((-2 * np.pi ** 2 * density_au + np.trapz(q, n1)) / np.trapz(q, n2))

    return n


def calculate_f_mean_squared(elemental_abundances, q):
    """
    calculates <f>^2 as defined in Waseda book
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :return:
    """
    norm_elemental_abundances = normalize_elemental_abundances(elemental_abundances)

    res = 0
    for key, value in norm_elemental_abundances.iteritems():
        res += value * calculate_coherent_scattering_factor(key, q)
    return res ** 2


def calculate_f_squared_mean(elemental_abundances, q):
    """
    calculates <f^2> as defined in Waseda book
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :return:
    """
    norm_elemental_abundances = normalize_elemental_abundances(elemental_abundances)

    res = 0
    for key, value in norm_elemental_abundances.iteritems():
        res += value * calculate_coherent_scattering_factor(key, q) ** 2
    return res


def calculate_incoherent_scattering(elemental_abundances, q):
    """
    Calculates compton/incoherent scattering for a compound
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :param q: q_values in reverse Angstrom
    :return: ndarray of compton scattering
    """
    norm_elemental_abundances = normalize_elemental_abundances(elemental_abundances)

    res = 0
    for key, value in norm_elemental_abundances.iteritems():
        res += value * calculate_incoherent_scattered_intensity(key, q)
    return res


def normalize_elemental_abundances(elemental_abundances):
    """
    normalizes elemental abundances to 1
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :return: normalized elemental abundances dictionary dictionary
    """
    sum = 0.0
    for key, val in elemental_abundances.iteritems():
        sum += val

    result = copy(elemental_abundances)

    for key in result:
        result[key] /= sum

    return result


def convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density):
    """
    Converts densities in g/cm3 into atoms per A^3
    :param elemental_abundances: dictionary with elements as key and abundances as relative numbers
    :param density: density in g/cm^3
    :return: density in atoms/A^3
    """

    # get_smallest abundance
    norm_elemental_abundances = normalize_elemental_abundances(elemental_abundances)
    mean_z = 0.0
    for key, val in norm_elemental_abundances.iteritems():
        mean_z += val * ScatteringFactors.atomic_weights['AW'][key]
    return density / mean_z * .602214129




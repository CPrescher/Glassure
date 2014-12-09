# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'


from ScatteringFactors import calculate_coherent_scattering_factor, calculate_incoherent_scattered_intensity
import ScatteringFactors

from copy import copy

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


# -*- coding: utf8 -*-
import numpy as np

from .scattering_factors import scattering_factor_param, calculate_coherent_scattering_factor, \
    calculate_incoherent_scattered_intensity


def calc_atomic_number_sum(composition):
    """
    Calculates the sum of the atomic number of all elements in the composition

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :return: sum of the atomic numbers
    """
    z_tot = 0
    for element, n in composition.items():
        z_tot += scattering_factor_param['Z'][element] * n
    return z_tot


def calculate_effective_form_factors(composition, q):
    """
    Calculates the effective form factor as defined in Eq. 10 in Eggert et al. (2002)

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param q: Q value or numpy array with a unit of A^-1
    :return: effective form factors numpy array
    """
    z_tot = calc_atomic_number_sum(composition)

    f_effective = 0
    for element, n in composition.items():
        f_effective += calculate_coherent_scattering_factor(element, q) * n

    return f_effective / float(z_tot)


def calculate_incoherent_scattering(composition, q):
    """
    Calculates the not normalized incoherent scattering contribution from a specific composition.

    :param composition:
    :param q: Q value or numpy array with a unit of A^-1
    :return: incoherent scattering numpy array
    """
    inc = 0
    for element, n in composition.items():
        inc += calculate_incoherent_scattered_intensity(element, q) * n

    return inc


def calculate_j(incoherent_scattering, z_tot, f_effective):
    """
    Calculates the J parameter as described in equation (35) from Eggert et al. 2002.

    :param incoherent_scattering: Q dependent incoherent scattering
    :param z_tot: sum of atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :return: J numpy array with the same q as incoherent scattering and f_effective
    """
    return incoherent_scattering / (z_tot * f_effective) ** 2


def calculate_kp(element, f_effective, q):
    """
    Calculates the average effective atomic number (averaged over the whole Q range).

    :param element: elemental symbol
    :param f_effective: effective form factor
    :param q: Q value or numpy array with a unit of A^-1
    :return: average effective atomic number
    :rtype: float
    """
    kp = np.mean(calculate_coherent_scattering_factor(element, q) / f_effective)
    return kp


def calculate_s_inf(composition, z_tot, f_effective, q):
    """
    Calculates S_inf as described in equation (19) from Eggert et al. 2002

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param z_tot: sum of atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :param q: q numpy array with units of A^-1
    :return: S_inv value
    """
    sum_kp_squared = 0
    for element, n in composition.items():
        sum_kp_squared += n * calculate_kp(element, f_effective, q) ** 2

    return sum_kp_squared/z_tot**2

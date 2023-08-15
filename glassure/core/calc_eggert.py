# -*- coding: utf-8 -*-
from typing import Optional
from copy import deepcopy

import numpy as np
from scipy.integrate import simps

from . import calculate_gr_raw
from .scattering_factors import calculate_coherent_scattering_factor, calculate_incoherent_scattered_intensity, \
    ScatteringFactorCalculatorHajdu
from .soller_correction import SollerCorrection
from .pattern import Pattern

scattering_factor_param = ScatteringFactorCalculatorHajdu().coherent_param


def calculate_atomic_number_sum(composition: dict[str, float]):
    """
    Calculates the sum of the atomic number of all elements in the composition

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :return: sum of the atomic numbers
    """
    z_tot = 0
    for element, n in composition.items():
        z_tot += scattering_factor_param['Z'][element] * n
    return z_tot


def calculate_effective_form_factors(composition: dict[str, float], q: np.ndarray) -> np.ndarray:
    """
    Calculates the effective form factor as defined in Eq. 10 in Eggert et al. (2002)

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param q: Q value or numpy array with a unit of A^-1
    :return: effective form factors numpy array
    """
    z_tot = calculate_atomic_number_sum(composition)

    f_effective = np.zeros_like(q)
    for element, n in composition.items():
        f_effective += calculate_coherent_scattering_factor(element, q) * n

    return f_effective / float(z_tot)


def calculate_incoherent_scattering(composition: dict[str, float], q: np.ndarray) -> np.ndarray:
    """
    Calculates the not normalized incoherent scattering contribution from a specific composition.

    :param composition:
    :param q: Q value or numpy array with a unit of A^-1
    :return: incoherent scattering numpy array
    """
    inc = np.zeros_like(q)
    for element, n in composition.items():
        inc += calculate_incoherent_scattered_intensity(element, q) * n

    return inc


def calculate_j(incoherent_scattering: np.ndarray, z_tot: float, f_effective: np.ndarray) -> np.ndarray:
    """
    Calculates the J parameter as described in equation (35) from Eggert et al. 2002.

    :param incoherent_scattering: Q dependent incoherent scattering
    :param z_tot: sum of atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :return: J numpy array with the same q as incoherent scattering and f_effective
    """
    return incoherent_scattering / (z_tot * f_effective) ** 2


def calculate_kp(element: str, f_effective: np.ndarray, q: np.ndarray) -> np.ndarray:
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


def calculate_s_inf(composition: dict[str, float], z_tot: float, f_effective: np.ndarray, q: np.ndarray) -> float:
    """
    Calculates S_inf as described in equation (19) from Eggert et al. 2002

    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param z_tot: sum of atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :param q: q numpy array with units of A^-1
    :return: S_inf value
    """
    sum_kp_squared = 0
    for element, n in composition.items():
        sum_kp_squared += n * calculate_kp(element, f_effective, q) ** 2

    return sum_kp_squared / z_tot ** 2


def calculate_alpha(sample_pattern: Pattern, z_tot: float, f_effective: np.ndarray, s_inf: np.ndarray, j: np.ndarray,
                    atomic_density: float) -> float:
    """
    Calculates the normalization factor alpha after equation (34) from Eggert et al. 2002.

    :param sample_pattern: Background subtracted sample pattern
    :param z_tot: sum opf atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :param s_inf: S_inf value (equ. (19) from Eggert et al. 2002)
    :param j: J value (equ. (35) from Eggert et al. 2002)
    :param atomic_density: number density in atoms/Angstrom^3
    :return: normalization factor alpha
    """

    q, intensity = sample_pattern.data

    integral_1 = simps((j + s_inf) * q ** 2, q)
    integral_2 = simps((intensity / f_effective ** 2) * q ** 2, q)

    alpha = z_tot ** 2 * (-2 * np.pi ** 2 * atomic_density + integral_1) / integral_2

    return alpha


def calculate_coherent_scattering(sample_pattern: Pattern, alpha: float, n: float,
                                  incoherent_scattering: np.ndarray) -> Pattern:
    """
    Calculates the coherent Scattering Intensity Pattern

    :param sample_pattern:  Background subtracted sample pattern
    :param alpha: normalization factor alpha (after equ. (34) from Eggert et al. 2002)
    :param n: Number of atoms
    :param incoherent_scattering: incoherent scattering intensity
    :return: Coherent Scattering Pattern
    :rtype: Pattern
    """

    q, intensity = sample_pattern.data
    coherent_intensity = n * (alpha * intensity - incoherent_scattering)
    return Pattern(q, coherent_intensity)


def calculate_sq(coherent_pattern: Pattern, n: float, z_tot: float, f_effective: np.ndarray) -> Pattern:
    """
    Calculates the Structure Factor based on equation (18) in Eggert et al. 2002
    :param coherent_pattern: coherent pattern
    :param n: number of atoms for structural unit, e.g. 3 for SiO2
    :param z_tot: sum of atomic numbers for the material
    :param f_effective: Q dependent effective form factor
    :return: S(q)
    """
    q, coherent_intensity = coherent_pattern.data
    sq_intensity = coherent_intensity / (n * z_tot ** 2 * f_effective ** 2)

    return Pattern(q, sq_intensity)


def calculate_fr(iq_pattern: Pattern, r: Optional[np.ndarray] = None, use_modification_fcn: bool = False) -> Pattern:
    """
    Calculates F(r) from a given interference function i(Q) for r values.
    If r is none a range from 0 to 10 with step 0.01 is used.    A Lorch modification function of the form:

        m = sin(q*pi/q_max)/(q*pi/q_max)

    can be used to address issues with a low q_max. This will broaden the sharp peaks in f(r)

    :param iq_pattern:             interference function i(q) = S(Q)-S_inf with lim_inf i(Q)=0 and unit(q)=A^-1
    :type iq_pattern: Pattern
    :param r:                       numpy array giving the r-values for which F(r) will be calculated,
                                    default is 0 to 10 with 0.01 as a step. units should be in Angstrom.
    :param use_modification_fcn:    boolean flag whether to use the Lorch modification function

    :return: F(r) pattern
    :rtype: Pattern
    """
    if r is None:
        r = np.arange(0, 10, 0.01)

    q, iq = iq_pattern.data
    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1

    fr = 2.0 / np.pi * simps(modification * q * iq * np.array(np.sin(np.outer(q.T, r))).T, q)

    return Pattern(r, fr)


def optimize_iq(iq_pattern, r_cutoff, iterations, atomic_density, j, s_inf=1, use_modification_fcn=False,
                attenuation_factor=1, fcn_callback=None, callback_period=2):
    """
    Performs an optimization of the structure factor based on an r_cutoff value as described in Eggert et al. 2002 PRB,
    65, 174105. This basically does back and forward transforms between S(Q) and f(r) until the region below the
    r_cutoff value is a flat line without any oscillations.

    :param iq_pattern:
        original i(Q) pattern = S(Q)-S_inf
    :param r_cutoff:
        cutoff value below which there is no signal expected (below the first peak in g(r))
    :param iterations:
        number of back and forward transforms
    :param atomic_density:
        density in atoms/A^3
    :param j:
        J value (equ. (35) from Eggert et al. 2002)
    :param s_inf:
        S_inf value (equ. (19) from Eggert et al. 2002, defaults to 1, which is the value for mon-atomic substances
    :param use_modification_fcn:
        Whether to use the Lorch modification function during the Fourier transform.
        Warning: When using the Lorch modification function usually more iterations are needed to get to the
        wanted result.
    :param attenuation_factor:
        Sometimes the initial change during back and forward transformations results in a runaway, by setting the
        attenuation factor to higher than one can help for this situation, it basically reduces
        the amount of change during each iteration.
    :param fcn_callback:
        Function which will be called at an iteration period defined by the callback_period parameter.
        The function should take 3 arguments: sq_pattern, fr_pattern and gr_pattern. Additionally the function
        should return a boolean value, where True continues the optimization and False will stop the optimization
        procedure
    :param callback_period:
        determines how frequently the fcn_callback will be called.

    :return:
        optimized S(Q) pattern
    """
    r = np.arange(0, r_cutoff, 0.02)
    iq_pattern = deepcopy(iq_pattern)
    for iteration in range(iterations):
        fr_pattern = calculate_fr(iq_pattern, r, use_modification_fcn)
        q, iq_int = iq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * atomic_density

        in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
        integral = np.trapz(in_integral, r) / attenuation_factor
        iq_optimized = iq_int - 1. / q * (iq_int / (s_inf + j) + 1) * integral

        iq_pattern = Pattern(q, iq_optimized)

        if fcn_callback is not None and iteration % callback_period == 0:
            fr_pattern = calculate_fr(iq_pattern, use_modification_fcn=use_modification_fcn)
            gr_pattern = calculate_gr_raw(fr_pattern, atomic_density)
            fcn_callback(iq_pattern, fr_pattern, gr_pattern)
    return iq_pattern


def calculate_chi2_map(data_pattern, bkg_pattern, composition,
                       densities, bkg_scalings, r_cutoff, iterations=2):
    """
    Calculates a chi2 2d array for an array of densities and background scalings.

    :param data_pattern: original data pattern
    :param bkg_pattern: original background pattern
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param densities: 1-dimensional array of densities for which to calculate chi2
    :param bkg_scalings: 1-dimensional array of background scalings for which to calculate chi2
    :param r_cutoff: cutoff value below which there is no signal expected (below the first peak in g(r))
    :param iterations: number of iterations for optimization, described in equations 47-49 in Eggert et al. 2002
    :return: 2-dimensional array of chi2 values
    """

    n = sum([composition[x] for x in composition])
    q = data_pattern.extend_to(0, 0).x

    inc = calculate_incoherent_scattering(composition, q)
    f_eff = calculate_effective_form_factors(composition, q)
    z_tot = calculate_atomic_number_sum(composition)
    s_inf = calculate_s_inf(composition, z_tot, f_eff, q)
    j = calculate_j(inc, z_tot, f_eff)

    chi2 = np.zeros((len(densities), len(bkg_scalings)))

    for n1, density in enumerate(densities):
        for n2, bkg_scaling in enumerate(bkg_scalings):
            # density = params['density'].value
            # bkg_scaling = params['bkg_scaling'].value

            r = np.arange(0, r_cutoff, 0.02)
            sample_pattern = data_pattern - bkg_scaling * bkg_pattern
            sample_pattern = sample_pattern.extend_to(0, 0)

            alpha = calculate_alpha(sample_pattern, z_tot, f_eff, s_inf, j, density)

            coherent_pattern = calculate_coherent_scattering(sample_pattern, alpha, n, inc)
            sq_pattern = calculate_sq(coherent_pattern, n, z_tot, f_eff)
            iq_pattern = Pattern(sq_pattern.x, sq_pattern.y - s_inf)

            delta_fr = np.zeros(r.shape)

            for iteration in range(iterations):
                fr_pattern = calculate_fr(iq_pattern, r)

                q, iq_int = iq_pattern.data
                r, fr_int = fr_pattern.data

                delta_fr = fr_int + 4 * np.pi * r * density

                in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
                integral = np.trapz(in_integral, r)
                iq_optimized = iq_int - 1. / q * (iq_int / (s_inf + j) + 1) * integral

                iq_pattern = Pattern(q, iq_optimized)

            chi2[n1, n2] = np.sum(delta_fr ** 2)
    return chi2


def optimize_density_and_bkg_scaling(data_pattern: Pattern, bkg_pattern: Pattern, composition: dict[str, float],
                                     initial_density: float, initial_bkg_scaling: float, r_cutoff: float,
                                     iterations: int = 2, use_modification_fcn: bool = False) \
        -> tuple[float, float, float, float]:
    """
    This function tries to find the optimum density in background scaling with the given parameters. The equations
    behind the optimization are presented equ (47-50) in the Eggert et al. 2002 paper.

    :param data_pattern: original data pattern
    :param bkg_pattern: original background pattern
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param initial_density: density starting point for the optimization procedure
    :param initial_bkg_scaling: background scaling starting point for the optimization procedure
    :param r_cutoff: cutoff value below which there is no signal expected (below the first peak in g(r))
    :param iterations: number of iterations for optimization, described in equations 47-49 in Eggert et al. 2002
    :param use_modification_fcn: Whether or not to use the Lorch modification function during the Fourier transform.
    :return: tuple with optimized parameters (density, density_error, bkg_scaling, bkg_scaling_error)
    """

    N = sum([composition[x] for x in composition])
    q = data_pattern.extend_to(0, 0).x

    inc = calculate_incoherent_scattering(composition, q)
    f_eff = calculate_effective_form_factors(composition, q)
    z_tot = calculate_atomic_number_sum(composition)
    s_inf = calculate_s_inf(composition, z_tot, f_eff, q)
    j = calculate_j(inc, z_tot, f_eff)

    def optimization_fcn(x):
        density = x['density'].value
        bkg_scaling = x['bkg_scaling'].value

        r = np.arange(0, r_cutoff, 0.02)
        sample_pattern = data_pattern - bkg_scaling * bkg_pattern
        sample_pattern = sample_pattern.extend_to(0, 0)

        alpha = calculate_alpha(sample_pattern, z_tot, f_eff, s_inf, j, density)

        coherent_pattern = calculate_coherent_scattering(sample_pattern, alpha, N, inc)
        sq_pattern = calculate_sq(coherent_pattern, N, z_tot, f_eff)
        iq_pattern = Pattern(sq_pattern.x, sq_pattern.y - s_inf)

        fr_pattern = calculate_fr(iq_pattern, r, use_modification_fcn=use_modification_fcn)

        q, iq_int = iq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * density

        for iteration in range(iterations):
            in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
            integral = np.trapz(in_integral, r)
            iq_optimized = iq_int - 1. / q * (iq_int / (s_inf + j) + 1) * integral

            iq_pattern = Pattern(q, iq_optimized)
            fr_pattern = calculate_fr(iq_pattern, r)

            q, iq_int = iq_pattern.data
            r, fr_int = fr_pattern.data

            delta_fr = fr_int + 4 * np.pi * r * density

        return delta_fr

    from lmfit import Parameters, minimize

    params = Parameters()
    params.add('density', value=initial_density, )
    params.add('bkg_scaling', value=initial_bkg_scaling)

    result = minimize(optimization_fcn, params)

    return result.params['density'].value, result.params['density'].stderr, \
        result.params['bkg_scaling'].value, result.params['density'].stderr


def optimize_soller_dac(data_pattern: Pattern, bkg_pattern: Pattern, composition: dict[str, float],
                        initial_density: float, initial_bkg_scaling: float, initial_thickness: float,
                        sample_thickness: float, wavelength: float, initial_carbon_content: float = 1,
                        r_cutoff: float = 2.28, iterations: int = 1, use_modification_fcn: bool = False,
                        vary: tuple[bool, bool, bool] = (True, True, True)) \
        -> tuple[float, float, float, float, float, float, float]:
    """
    Optimizes density, background scaling and diamond content for a list of sample thickness with a given initial
    gasket thickness in the diamond anvil cell (DAC). The calculation is done by utilizing the soller slit transfer
    function and assuming that the DAC has been centered to the rotation center of the soller slit.

    :param data_pattern: original data pattern
    :param bkg_pattern: original background pattern
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param initial_density: density starting point for the optimization procedure
    :param initial_bkg_scaling: background scaling starting point for the optimization procedure
    :param initial_thickness: gasket thickness with which the background was measured.
    :param sample_thickness: sample thickness for which the sample was measured
    :param wavelength: wavelength of the radiation used - needed for calculation of soller slit transfer function in
                       q-space
    :param initial_carbon_content: carbon content starting point for the optimization
    :param r_cutoff: cutoff value below which there is no signal expected (below the first peak in g(r)
    :param iterations: number of iterations for optimization, described in equations 47-49 in Eggert et al. 2002
    :param use_modification_fcn: Whether or not to use the Lorch modification function during the Fourier transform.
    :param vary: 3 boolean flags whether to vary: density, bkg_scaling, carbon_content during the optimization
    :return:
    """
    n = sum([composition[x] for x in composition])
    q = data_pattern.extend_to(0, 0).x

    inc = calculate_incoherent_scattering(composition, q)
    f_eff = calculate_effective_form_factors(composition, q)
    z_tot = calculate_atomic_number_sum(composition)
    s_inf = calculate_s_inf(composition, z_tot, f_eff, q)
    j = calculate_j(inc, z_tot, f_eff)

    tth = 2 * np.arcsin(data_pattern.x * wavelength / (4 * np.pi)) / np.pi * 180
    soller = SollerCorrection(tth, initial_thickness)

    def optimization_fcn(params):
        diamond_content = params['diamond_content'].value
        bkg_scaling = params['bkg_scaling'].value
        density = params['density'].value

        q, data_int = data_pattern.data
        _, bkg_int = bkg_pattern.data

        sample_transfer, diamond_transfer = soller.transfer_function_dac(sample_thickness, initial_thickness)

        diamond_background = diamond_content * Pattern(q,
                                                       calculate_incoherent_scattering({'C': 1},
                                                                                       q) / diamond_transfer)

        sample_pattern = data_pattern - bkg_scaling * bkg_pattern
        sample_pattern = sample_pattern - diamond_background
        sample_pattern = Pattern(q, sample_pattern.y * sample_transfer)
        sample_pattern = sample_pattern.extend_to(0, 0)

        alpha = calculate_alpha(sample_pattern, z_tot, f_eff, s_inf, j, density)

        coherent_pattern = calculate_coherent_scattering(sample_pattern, alpha, n, inc)
        sq_pattern = calculate_sq(coherent_pattern, n, z_tot, f_eff)
        iq_pattern = Pattern(sq_pattern.x, sq_pattern.y - s_inf)

        r = np.arange(0, r_cutoff, 0.02)
        fr_pattern = calculate_fr(iq_pattern, r, use_modification_fcn=use_modification_fcn)

        q, iq_int = iq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * density

        for iteration in range(iterations):
            in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
            integral = np.trapz(in_integral, r)
            iq_optimized = iq_int - 1. / q * (iq_int / (s_inf + j) + 1) * integral

            iq_pattern = Pattern(q, iq_optimized)
            fr_pattern = calculate_fr(iq_pattern, r)

            q, iq_int = iq_pattern.data
            r, fr_int = fr_pattern.data

            delta_fr = fr_int + 4 * np.pi * r * density

        return delta_fr

    from lmfit import Parameters, minimize, report_fit

    params = Parameters()
    params.add('density', value=initial_density, min=0, vary=vary[0])
    params.add('bkg_scaling', value=initial_bkg_scaling, vary=vary[1])
    params.add('diamond_content', value=initial_carbon_content, min=0, vary=vary[2])

    result = minimize(optimization_fcn, params)

    report_fit(result)

    return result.chisqr, \
        result.params['density'].value, result.params['density'].stderr, \
        result.params['bkg_scaling'].value, result.params['bkg_scaling'].stderr, \
        result.params['diamond_content'].value, result.params['diamond_content'].stderr

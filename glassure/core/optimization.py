# -*- coding: utf8 -*-

from copy import deepcopy

import numpy as np
import lmfit

from . import Pattern
from .calc import calculate_fr, calculate_gr_raw, calculate_sq, calculate_sq_raw, calculate_normalization_factor_raw, \
    fit_normalization_factor
from .utility import convert_density_to_atoms_per_cubic_angstrom, calculate_incoherent_scattering, \
    calculate_f_mean_squared, calculate_f_squared_mean
from .utility import extrapolate_to_zero_poly
from .soller_correction import SollerCorrection


__all__ = ['optimize_sq', 'optimize_density', 'optimize_incoherent_container_scattering',
           'optimize_soller_dac']


def optimize_sq(sq_pattern, r_cutoff, iterations, atomic_density, use_modification_fcn=False,
                attenuation_factor=1, fcn_callback=None, callback_period=2):
    """
    Performs an optimization of the structure factor based on an r_cutoff value as described in Eggert et al. 2002 PRB,
    65, 174105. This basically does back and forward transforms between S(Q) and f(r) until the region below the
    r_cutoff value is a flat line without any oscillations.

    :param sq_pattern:
        original S(Q)
    :param r_cutoff:
        cutoff value below which there is no signal expected (below the first peak in g(r))
    :param iterations:
        number of back and forward transforms
    :param atomic_density:
        density in atoms/A^3
    :param use_modification_fcn:
        Whether or not to use the Lorch modification function during the Fourier transform.
        Warning: When using the Lorch modification function usually more iterations are needed to get to the
        wanted result.
    :param attenuation_factor:
        Sometimes the initial change during back and forward transformations results in a run
        away, by setting the attenuation factor to higher than one can help for this situation, it basically reduces
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
    sq_pattern = deepcopy(sq_pattern)
    for iteration in range(iterations):
        fr_pattern = calculate_fr(sq_pattern, r, use_modification_fcn)
        q, sq_int = sq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * atomic_density

        in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
        integral = np.trapz(in_integral, r) / attenuation_factor
        sq_optimized = sq_int * (1 - 1. / q * integral)

        sq_pattern = Pattern(q, sq_optimized)

        if fcn_callback is not None and iteration % callback_period == 0:
            fr_pattern = calculate_fr(sq_pattern, use_modification_fcn=use_modification_fcn)
            gr_pattern = calculate_gr_raw(fr_pattern, atomic_density)
            fcn_callback(sq_pattern, fr_pattern, gr_pattern)
    return sq_pattern


def optimize_density(data_pattern, background_pattern, initial_background_scaling, composition,
                     initial_density, background_min, background_max, density_min, density_max,
                     iterations, r_cutoff, use_modification_fcn=False, extrapolation_cutoff=None,
                     r_step=0.01, fcn_callback=None):
    """
    Performs an optimization of the background scaling and density using a figure of merit function defined by the low
    r region in F(r) as described in Eggert et al. (2002) PRB, 65, 174105.

    :param data_pattern:       raw data pattern in Q space (A^-1)
    :param background_pattern: raw background pattern in Q space (A^-1)
    :param initial_background_scaling:
                                start value for the background scaling optimization
    :param composition:         composition of the sample as a dictionary with elements as keys and abundances as values
    :param initial_density:     start value for the density optimization in g/cm^3
    :param background_min:      minimum value for the background scaling
    :param background_max:      maximum value for the background scaling
    :param density_min:         minimum value for the density
    :param density_max:         maximum value for the density
    :param iterations:          number of iterations of S(Q) (see optimize_sq(...) prior to calculating chi2
    :param r_cutoff:            cutoff value below which there is no signal expected (below the first peak in g(r))
    :param use_modification_fcn:
                                Whether or not to use the Lorch modification function during the Fourier transform.
                                Warning: When using the Lorch modification function usually more iterations are needed
                                to get to the wanted result. Default is False.
    :param extrapolation_cutoff:
                                Determines up to which q value the S(Q) will be extrapolated to zero. The default
                                (None), will use the minimum q value plus 0.2 A^-1
    :param r_step:              Step size for the r-space for calculating f(r) during each iteration. Defaults to
                                0.01.
    :param fcn_callback:        Function which will be called after each iteration. The function should take 4
                                arguments: iteration number, chi2, density, and background scaling. Additionally the
                                function should return a boolean value, where True continues the optimization and False
                                will stop the optimization procedure

    :return: (tuple) - density, density standard error, background scaling, background scaling standard error
    """
    params = lmfit.Parameters()
    params.add("density", value=initial_density, min=density_min, max=density_max)
    params.add("background_scaling", value=initial_background_scaling, min=background_min, max=background_max)

    r = np.arange(0, r_cutoff + r_step / 2., r_step)

    def optimization_fcn(params, extrapolation_max, r, r_cutoff, use_modification_fcn):
        density = params['density'].value
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
        background_pattern.scaling = params['background_scaling'].value

        sq = calculate_sq(data_pattern - background_pattern, density, composition)
        extrapolation_max = extrapolation_max or np.min(sq._x[0]) + 0.2
        sq = extrapolate_to_zero_poly(sq, extrapolation_max)
        sq_optimized = optimize_sq(sq, r_cutoff, iterations, atomic_density, use_modification_fcn)
        fr = calculate_fr(sq_optimized, r=r, use_modification_fcn=use_modification_fcn)

        min_r, min_fr = fr.data

        output = (min_fr + 4 * np.pi * atomic_density * min_r) ** 2 * r_step

        if fcn_callback is not None:
            if not fcn_callback(optimization_fcn.iteration,
                                np.sum(output),
                                density,
                                params['background_scaling'].value):
                return None
        optimization_fcn.iteration += 1
        return output

    optimization_fcn.iteration = 1

    lmfit.minimize(optimization_fcn, params, args=(extrapolation_cutoff, r, r_cutoff, use_modification_fcn))
    lmfit.report_fit(params)

    return params['density'].value, params['density'].stderr, \
           params['background_scaling'].value, params['background_scaling'].stderr


def optimize_incoherent_container_scattering(sample_pattern, sample_density, sample_composition, container_composition,
                                             r_cutoff, initial_content=10, use_extrapolation=True,
                                             extrapolation_q_max=None, callback_fcn=None):
    """
    Finds the amount of extra scattering from a sample container which was not included in the
    background measurement. A typical use-case are diamond anvil cell experiments were the background is usually
    collected for an empty cell with a gasket of a specific thickness. However, during compression the gasket will
    shrink in thickness and additional diamond compton (incoherent) scattering will be in the resulting data.

    The function tries to achieve this by varying the amount of incoherent scattering from the container and minimizing
    on the intensities of g(r) below a chosen r_cutoff. The r_cutoff parameter should be chosen to be below the first
    peak in g(r) -- usually somewhere between 1 and 1.5 for e.g. silicates and depending on you q_max for the data
    collection.

    :param sample_pattern:     Background subtracted data pattern
    :param sample_density:      density of the sample in g/cm^3
    :param sample_composition:  composition of the sample as a dictionary with elements as keys and abundances as values
    :param container_composition:
                                composition of the container_as a dictionary with the elements as keys and the
                                abundances as values
    :param r_cutoff:            an r cutoff for the g(r) in Angstrom for the area used for optimization. Should be
                                below the first peak (basically defines the region where g(r) should be zero for ideal data)
    :param initial_content:     starting content for the optimization
    :param use_extrapolation:   whether to use extrapolation (polynomial) to zero for S(Q) or not prior to transforming it to F(r)
    :param extrapolation_q_max: defines the q range for which the extrapolation to zero will be fitted. Default value
                                (None) which takes the q_min of the sample pattern and adds 0.2 and uses that as a
                                range.
    :param callback_fcn:        function which will be called during each iteration of the optimization. The function s
                                should have an interface for the following parameters:
                                      - background_content - dimensionless number describing the amount of
                                                            incoherent scattering  optimized
                                      - scaled_incoherent_background - calculated scaled incoherent background
                                      - sq - S(Q) calculated using the scaled incoherent background
                                      - fr - F(r) calculated using the scaled incoherent background
                                      - gr - g(r) calculated using the scaled incoherent background

    :return: (tuple) background_content as dimensionless number, scaled incoherent background pattern
    """
    q, _ = sample_pattern.data

    incoherent_background_pattern = Pattern(q, calculate_incoherent_scattering(container_composition, q))
    params = lmfit.Parameters()
    params.add("content", value=initial_content, min=0)

    if extrapolation_q_max is None:
        extrapolation_q_max = np.min(q) + 0.2

    sample_atomic_density = convert_density_to_atoms_per_cubic_angstrom(sample_composition, sample_density)
    sample_incoherent_scattering = calculate_incoherent_scattering(sample_composition, q)
    sample_f_mean_squared = calculate_f_mean_squared(sample_composition, q)
    sample_f_squared_mean = calculate_f_squared_mean(sample_composition, q)

    def optimization_fcn(params):
        background_content = params['content'].value

        incoherent_background_pattern.scaling = background_content
        subtracted_sample_pattern = sample_pattern - incoherent_background_pattern
        sample_normalization_factor = calculate_normalization_factor_raw(
            subtracted_sample_pattern,
            atomic_density=sample_atomic_density,
            f_squared_mean=sample_f_squared_mean,
            f_mean_squared=sample_f_mean_squared,
            incoherent_scattering=sample_incoherent_scattering
        )

        sq = calculate_sq_raw(
            subtracted_sample_pattern,
            f_squared_mean=sample_f_squared_mean,
            f_mean_squared=sample_f_mean_squared,
            incoherent_scattering=sample_incoherent_scattering,
            normalization_factor=sample_normalization_factor
        )

        sq = extrapolate_to_zero_poly(sq, extrapolation_q_max)

        fr = calculate_fr(sq)
        gr = calculate_gr_raw(fr, atomic_density=sample_atomic_density)

        low_r_gr = gr.limit(0, r_cutoff)
        if callback_fcn is not None:
            callback_fcn(background_content, incoherent_background_pattern, sq, fr, gr)

        return low_r_gr.data[1]

    lmfit.minimize(optimization_fcn, params)
    incoherent_background_pattern.scaling = params['content'].value

    return params['content'].value, incoherent_background_pattern


def optimize_soller_dac(data_pattern, bkg_pattern, composition, initial_density, initial_bkg_scaling,
                        initial_thickness, sample_thickness, wavelength,
                        initial_carbon_content=1, r_cutoff=2.28, iterations=1,
                        use_modification_fcn=False, vary=(True, True, True),
                        normalization_method='int', verbose=False):
    """
    Optimizes density, background scaling and diamond content for a list of sample thickness with a given initial
    gasket thickness in the diamond anvil cell (DAC). The calculation is done by utilizing the soller slit transfer
    function and assuming that the DAC has been centered to the rotation center of the soller slit.

    :param data_pattern: original data pattern
    :param bkg_pattern: original background pattern
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param initial_density: number density starting point for the optimization procedure
    :param initial_bkg_scaling: background scaling starting point for the optimization procedure
    :param initial_thickness: gasket thickness with which the background was measured in mm
    :param sample_thickness: sample thickness for which the sample was measured in mm
    :param wavelength: wavelength of the radiation used - needed for calculation of soller slit transfer function in
                       q-space in Angstrom
    :param initial_carbon_content: carbon content starting point for the optimization
    :param r_cutoff: cutoff value below which there is no signal expected (below the first peak in g(r)
    :param iterations: number of iterations for optimization, described in equations 47-49 in Eggert et al. 2002
    :param use_modification_fcn: Whether or not to use the Lorch modification function during the Fourier transform.
    :param vary: 3 boolean flags whether to vary: density, bkg_scaling, carbon_content during the optimization
    :param normalization_method: determines the method used for estimating the normalization method. possible values are
                                 'int' for an integral or 'fit' for fitting the high q region form factors.
    :param verbose: boolean flag whether to print out a fit report or not
    :return:
    """

    q = data_pattern.extend_to(0, 0).x

    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    incoherent_scattering = calculate_incoherent_scattering(composition, q)

    tth = 2 * np.arcsin(data_pattern.x * wavelength / (4 * np.pi)) / np.pi * 180
    soller = SollerCorrection(tth, initial_thickness)
    sample_transfer, diamond_transfer = soller.transfer_function_dac(sample_thickness, initial_thickness)


    def optimization_fcn(params):
        diamond_content = params['diamond_content'].value
        bkg_scaling = params['bkg_scaling'].value
        density = params['density'].value

        q, data_int = data_pattern.data
        _, bkg_int = bkg_pattern.data

        diamond_background = diamond_content * Pattern(q,
                                                       calculate_incoherent_scattering({'C': 1},
                                                                                       q) / diamond_transfer)

        sample_pattern = data_pattern - bkg_scaling * bkg_pattern
        sample_pattern = sample_pattern - diamond_background
        sample_pattern = Pattern(q, sample_pattern.y * sample_transfer)
        sample_pattern = sample_pattern.extend_to(0, 0)

        if normalization_method == 'fit':
            normalization_factor = fit_normalization_factor(sample_pattern, composition)
        else:
            normalization_factor = calculate_normalization_factor_raw(sample_pattern, density, f_squared_mean,
                                                                  f_mean_squared, incoherent_scattering)

        sq_pattern = calculate_sq_raw(sample_pattern=sample_pattern,
                                      f_squared_mean=f_squared_mean,
                                      f_mean_squared=f_mean_squared,
                                      incoherent_scattering=incoherent_scattering,
                                      normalization_factor=normalization_factor)

        r = np.arange(0, r_cutoff, 0.05)
        fr_pattern = calculate_fr(sq_pattern=sq_pattern, r=r, use_modification_fcn=use_modification_fcn)

        q, sq_int = sq_pattern.data
        r, fr_int = fr_pattern.data
        iq_int = sq_int-1

        delta_fr = fr_int + 4 * np.pi * r * density

        for iteration in range(iterations):
            in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
            integral = np.trapz(in_integral, r)
            iq_optimized = iq_int - 1. / q * (iq_int + 1) * integral

            iq_pattern = Pattern(q, iq_optimized)
            fr_pattern = calculate_fr(Pattern(q, iq_optimized+1), r)

            q, iq_int = iq_pattern.data
            r, fr_int = fr_pattern.data

            delta_fr = fr_int + 4 * np.pi * r * density

        return delta_fr/len(delta_fr)


    from lmfit import Parameters, minimize, report_fit

    params = Parameters()
    params.add('density', value=initial_density, min=0, vary=vary[0])
    params.add('bkg_scaling', value=initial_bkg_scaling, vary=vary[1])
    params.add('diamond_content', value=initial_carbon_content, min=0, vary=vary[2])

    result = minimize(optimization_fcn, params)

    if verbose:
        report_fit(result)

    return result.chisqr, \
           result.params['density'].value, result.params['density'].stderr, \
           result.params['bkg_scaling'].value, result.params['bkg_scaling'].stderr, \
           result.params['diamond_content'].value, result.params['diamond_content'].stderr

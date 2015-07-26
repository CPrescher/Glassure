__author__ = 'Clemens Prescher'

from copy import deepcopy

import numpy as np
import lmfit

from . import Spectrum
from utility import calculate_incoherent_scattering, calculate_f_squared_mean, calculate_f_mean_squared, \
    convert_density_to_atoms_per_cubic_angstrom, extrapolate_to_zero_poly

__all__ = ['calculate_normalization_factor_raw', 'calculate_normalization_factor',
           'calculate_sq', 'calculate_sq_raw', 'calculate_sq_from_gr',
           'calculate_fr', 'calculate_gr_raw', 'calculate_gr',
           'optimize_sq', 'optimize_density', 'optimize_incoherent_container_scattering']


def calculate_normalization_factor_raw(sample_spectrum, atomic_density, f_squared_mean, f_mean_squared,
                                       incoherent_scattering, attenuation_factor=0.001):
    """
    Calculates the normalization factor for a sample spectrum given all the parameters. If you do not have them
    already calculated please consider using calculate_normalization_factor, which has an easier interface since it
    just requires density and composition as parameters.

    :param sample_spectrum: background subtracted sample spectrum
    :param atomic_density: density in atoms per cubic Angstrom
    :param f_squared_mean: <f^2>
    :param f_mean_squared: <f>^2
    :param incoherent_scattering:
    :param attenuation_factor: attenuation factor used in the exponential, in order to correct for the q cutoff
    :return: normalization factor
    """
    q, intensity = sample_spectrum.data
    # calculate values for integrals
    n1 = q ** 2 * ((f_squared_mean + incoherent_scattering) * np.exp(-attenuation_factor * q ** 2)) / \
         f_mean_squared
    n2 = q ** 2 * intensity * np.exp(-attenuation_factor * q ** 2) / f_mean_squared

    n = ((-2 * np.pi ** 2 * atomic_density + np.trapz(q, n1)) / np.trapz(q, n2))

    return n


def calculate_normalization_factor(sample_spectrum, density, composition, attenuation_factor=0.001):
    """
    Calculates the normalization factor for a background subtracted sample spectrum based on density and composition.

    :param sample_spectrum: background subtracted sample spectrum with A-1 as x unit
    :param density: density in g/cm^3
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor: attenuation factor used in the exponential, in order to correct for the q cutoff
    :return: normalization factor
    """
    q, intensity = sample_spectrum.data

    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    incoherent_scattering = calculate_incoherent_scattering(composition, q)
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)

    return calculate_normalization_factor_raw(sample_spectrum, atomic_density, f_squared_mean, f_mean_squared,
                                              incoherent_scattering, attenuation_factor)


def calculate_sq_raw(sample_spectrum, f_squared_mean, f_mean_squared, incoherent_scattering, normalization_factor,
                     extra_correction=0):
    """
    Calculates the structure factor of a material with the given parameters. Using the equation:

    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1

    where n is the normalization factor and f are the scattering factors.

    :param sample_spectrum: background subtracted sample spectrum with A^-1 as x unit
    :param f_squared_mean: <f^2>
    :param f_mean_squared: <f>^2
    :param incoherent_scattering: compton scattering from sample
    :param normalization_factor: previously calculated normalization factor
    :return: S(Q) spectrum
    """
    q, intensity = sample_spectrum.data
    sq = (normalization_factor * intensity - incoherent_scattering - f_squared_mean) / f_mean_squared + 1
    return Spectrum(q, sq)


def calculate_sq(sample_spectrum, density, composition, attenuation_factor=0.001):
    """
    Calculates the structure factor of a material with the given parameters. Using the equation:

    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1

    where n is the normalization factor and f are the scattering factors. All parameters from the equation are
    calculated from the density, composition and the sample spectrum

    :param sample_spectrum: background subtracted sample spectrum with A^-1 as x unit
    :param density: density of the sample in g/cm^3
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor: attenuation factor used in the exponential for the calculation of the normalization
    factor
    :return: S(Q) spectrum
    """
    q, intensity = sample_spectrum.data
    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    incoherent_scattering = calculate_incoherent_scattering(composition, q)
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
    normalization_factor = calculate_normalization_factor_raw(sample_spectrum,
                                                              atomic_density,
                                                              f_squared_mean,
                                                              f_mean_squared,
                                                              incoherent_scattering,
                                                              attenuation_factor)
    return calculate_sq_raw(sample_spectrum,
                            f_squared_mean,
                            f_mean_squared,
                            incoherent_scattering,
                            normalization_factor)


def calculate_sq_from_gr(gr_spectrum, q, density, composition, use_modification_fcn=False):
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
    r, gr = gr_spectrum.data
    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1

    integral = 0
    dr = r[2] - r[1]
    for ind, r_val in enumerate(r):
        integral += r_val * (gr[ind] - 1) * np.sin(q * r_val) / q

    integral = integral * modification * dr
    intensity = 4 * np.pi * atomic_density * integral

    return Spectrum(q, intensity)


def calculate_fr(sq_spectrum, r=None, use_modification_fcn=False):
    """
    Calculates F(r) from a given S(Q) spectrum for r values. If r is none a range from 0 to 10 with step 0.01 is used.
    A Lorch modification function of the form:

        m = sin(q*pi/q_max)/(q*pi/q_max)

    can be used to address issues with a low q_max. This will broaden the sharp peaks in g(r)

    :param sq_spectrum: Structure factor S(Q) with lim_inf S(Q) = 1 and unit(q)=A^-1
    :param r: a numpy array giving the r-values for which F(r) will be calculated, default is 0 to 10 with 0.01 as a
    step. units should be in Angstrom.
    :param use_modification_fcn: boolean flag whether to use the Lorch modification function
    :return: F(r) spectrum
    """
    if r is None:
        r = np.linspace(0, 10, 1000)

    q, sq = sq_spectrum.data
    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1
    fr = 2.0 / np.pi * np.trapz(modification * q * (sq - 1) * \
                                np.array(np.sin(np.mat(q).T * np.mat(r))).T, q)
    return Spectrum(r, fr)


def calculate_gr_raw(fr_spectrum, atomic_density):
    """
    Calculates a g(r) spectrum from a given F(r) spectrum and the atomic density

    :param fr_spectrum: F(r) spectrum
    :param atomic_density: atomic density in atoms/A^3
    :return: g(r) spectrum
    """
    r, f_r = fr_spectrum.data
    g_r = 1 + f_r / (4.0 * np.pi * r * atomic_density)
    return Spectrum(r, g_r)


def calculate_gr(fr_spectrum, density, composition):
    """
    Calculates a g(r) spectrum from a given F(r) spectrum, the material density and composition.

    :param fr_spectrum: F(r) spectrum
    :param density: density in g/cm^3
    :param composition: composition as a dictionary with the elements as keys and the abundances as values
    :return: g(r) spectrum
    """
    return calculate_gr_raw(fr_spectrum, convert_density_to_atoms_per_cubic_angstrom(composition, density))


def optimize_sq(sq_spectrum, r_cutoff, iterations, atomic_density, use_modification_fcn=False,
                attenuation_factor=1, fcn_callback=None, callback_period=2):
    r = np.arange(0, r_cutoff, 0.02)
    sq_spectrum = deepcopy(sq_spectrum)
    for iteration in range(iterations):
        fr_spectrum = calculate_fr(sq_spectrum, r, use_modification_fcn)
        q, sq_int = sq_spectrum.data
        r, fr_int = fr_spectrum.data

        delta_fr = fr_int + 4 * np.pi * r * atomic_density

        in_integral = np.array(np.sin(np.mat(q).T * np.mat(r))) * delta_fr
        integral = np.trapz(in_integral, r) / attenuation_factor
        sq_optimized = sq_int * (1 - 1. / q * integral)

        sq_spectrum = Spectrum(q, sq_optimized)

        if fcn_callback is not None and iteration % 5 == 0:
            # fr_spectrum = self.calc_fr()
            # gr_spectrum = self.calc_gr()
            # fcn_callback(sq_spectrum, gr_spectrum)
            pass
    return sq_spectrum


def optimize_density(data_spectrum, background_spectrum, initial_background_scaling, composition,
                     initial_density, background_min, background_max, density_min, density_max,
                     iterations, r_cutoff,
                     use_modification_fcn=False, extrapolation_max=None, r=np.linspace(0, 10, 1000)):
    params = lmfit.Parameters()
    params.add("density", value=initial_density, min=density_min, max=density_max)
    params.add("background_scaling", value=initial_background_scaling, min=background_min, max=background_max)

    r_step = r[1] - r[0]

    def optimization_fcn(params, extrapolation_max, r, r_cutoff, use_modification_fcn):
        density = params['density'].value
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
        background_spectrum.scaling = params['background_scaling'].value

        sq = calculate_sq(data_spectrum - background_spectrum, density, composition)
        extrapolation_max = extrapolation_max or np.min(sq._x[0]) + 0.2
        sq = extrapolate_to_zero_poly(sq, extrapolation_max)
        sq_optimized = optimize_sq(sq, r_cutoff, iterations, atomic_density, use_modification_fcn)
        fr = calculate_fr(sq_optimized, r=r, use_modification_fcn=use_modification_fcn)

        min_r, min_fr = fr.limit(0, r_cutoff).data

        output = (min_fr + 4 * np.pi * atomic_density * min_r) ** 2 * r_step

        print('{:003d}: {:.4f}, {:.3f}, {:.3f}'.format(optimization_fcn.iteration,
                                                       np.sum(output),
                                                       density,
                                                       params['background_scaling'].value))
        optimization_fcn.iteration += 1

        return output

    optimization_fcn.iteration = 1

    lmfit.minimize(optimization_fcn, params, args=(extrapolation_max, r, r_cutoff, use_modification_fcn))
    lmfit.report_fit(params)

    return params['density'].value, params['density'].stderr, \
           params['background_scaling'].value, params['background_scaling'].stderr


def optimize_incoherent_container_scattering(sample_spectrum, sample_density, sample_composition, container_composition,
                                             r_cutoff, initial_content=10, use_extrapolation=True,
                                             extrapolation_q_max=None, callback_fcn=None):
    """
    This function tries to find the amount of extra scattering from a sample container which was not included in the
    background measurement. A typical use-case are diamond anvil cell experiments were the background is usually
    collected for an empty cell with a gasket of a specific thickness. However, during compression the gasket will
    shrink in thickness and additional diamond compton (incoherent) scattering will be in the resulting data.

    The function tries to achieve this by varying the amount of incoherent scattering from the container and minimizing
    on the intensities of g(r) below a chosen r_cutoff. The r_cutoff parameter should be chosen to be below the first
    peak in g(r) -- usually somewhere between 1 and 1.5 for e.g. silicates and depending on you q_max for the data
    collection.

    :param sample_spectrum: Background subtracted data spectrum
    :param sample_density: density of the sample in g/cm^3
    :param sample_composition: composition of the sample as a dictionary with elements as keys and abundances as values
    :param container_composition: composition of the container_as a dictionary with the elements as keys and the
    abundances as values
    :param r_cutoff: an r cutoff for the g(r) in Angstrom for the area used for optimization. Should be below the first
    peak (basically defines the region where g(r) should be zero for ideal data)
    :param initial_content: starting content for the optimization
    :param use_extrapolation: whether to use extrapolation (polynomial) to zero for S(Q) or not prior to transforming it to F(r)
    :param extrapolation_q_max: defines the q range for which the extrapolation to zero will be fitted. Default value
    (None) which takes the q_min of the sample spectrum and adds 0.2 and uses that as a range.
    :param callback_fcn: function which will be called during each iteration of the optimization. The function should
    have an interface for the following parameters:
      - background_content - dimensionless number describing the amount of incoherent scattering  optimized
      - scaled_incoherent_background - calculated scaled incoherent background
      - sq - S(Q) calculated using the scaled incoherent background
      - fr - F(r) calculated using the scaled incoherent background
      - gr - g(r) calculated using the scaled incoherent background
    :return: a tuple with background_content as dimensionless number as first element and the scaled incoherent
    background spectrum as second
    """
    q, _ = sample_spectrum.data

    incoherent_background_spectrum = Spectrum(q, calculate_incoherent_scattering(container_composition, q))
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

        incoherent_background_spectrum.scaling = background_content
        subtracted_sample_spectrum = sample_spectrum - incoherent_background_spectrum
        sample_normalization_factor = calculate_normalization_factor_raw(
            subtracted_sample_spectrum,
            atomic_density=sample_atomic_density,
            f_squared_mean=sample_f_squared_mean,
            f_mean_squared=sample_f_mean_squared,
            incoherent_scattering=sample_incoherent_scattering
        )

        sq = calculate_sq_raw(
            subtracted_sample_spectrum,
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
            callback_fcn(background_content, incoherent_background_spectrum, sq, fr, gr)

        return low_r_gr.data[1]

    lmfit.minimize(optimization_fcn, params)
    incoherent_background_spectrum.scaling = params['content'].value

    return params['content'].value, incoherent_background_spectrum

__author__ = 'Clemens Prescher'

import numpy as np
import lmfit

from . import Spectrum
from .utility import calculate_incoherent_scattering, calculate_f_squared_mean, calculate_f_mean_squared, \
    convert_density_to_atoms_per_cubic_angstrom

__all__ = ['calculate_normalization_factor_raw', 'calculate_normalization_factor',
           'calculate_sq', 'calculate_sq_raw', 'calculate_sq_from_gr',
           'calculate_fr', 'calculate_gr_raw', 'calculate_gr']


def calculate_normalization_factor_raw(sample_spectrum, atomic_density, f_squared_mean, f_mean_squared,
                                       incoherent_scattering, attenuation_factor=0.001):
    """
    Calculates the normalization factor for a sample spectrum given all the parameters. If you do not have them
    already calculated please consider using calculate_normalization_factor, which has an easier interface since it
    just requires density and composition as parameters.

    :param sample_spectrum:     background subtracted sample spectrum
    :param atomic_density:      density in atoms per cubic Angstrom
    :param f_squared_mean:      <f^2>
    :param f_mean_squared:      <f>^2
    :param incoherent_scattering: compton scattering from sample
    :param attenuation_factor:  attenuation factor used in the exponential, in order to correct for the q cutoff

    :return:                    normalization factor
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

    :param sample_spectrum:     background subtracted sample spectrum with A-1 as x unit
    :param density:             density in g/cm^3
    :param composition:         composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor:  attenuation factor used in the exponential, in order to correct for the q cutoff

    :return: normalization factor
    """
    q, intensity = sample_spectrum.data

    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    incoherent_scattering = calculate_incoherent_scattering(composition, q)
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)

    return calculate_normalization_factor_raw(sample_spectrum, atomic_density, f_squared_mean, f_mean_squared,
                                              incoherent_scattering, attenuation_factor)


def fit_normalization_factor(sample_spectrum, composition, q_cutoff=3, method="squared"):
    """
    Estimates the normalization factor n for calculating S(Q) by fitting

        (Intensity*n-Multiple Scattering) * Q^2
    to
        (Incoherent Scattering + Self Scattering) * Q^2

    where n and Multiple Scattering are free parameters

    :param sample_spectrum: background subtracted sample spectrum with A^-1 as x unit
    :param composition:     composition as a dictionary with the elements as keys and the abundances as values
    :param q_cutoff:        q value above which the fitting will be performed, default = 3
    :param method:          specifies whether q^2 ("squared") or q (linear) should be used

    :return: normalization factor
    """
    q, intensity = sample_spectrum.limit(q_cutoff, 100000).data

    if method == "squared":
        x = q ** 2
    elif method == "linear":
        x = q
    else:
        raise NotImplementedError("{} is not an allowed method for fit_normalization_factor".format(method))

    theory = (calculate_incoherent_scattering(composition, q) + calculate_f_squared_mean(composition, q)) * x

    params = lmfit.Parameters()
    params.add("n", value=1, min=0)
    params.add("multiple", value=1, min=0)

    def optimization_fcn(params, q, sample_intensity, theory_intensity):
        n = params['n'].value
        multiple = params['multiple'].value
        return ((sample_intensity * n - multiple) * x - theory_intensity) ** 2

    out = lmfit.minimize(optimization_fcn, params, args=(q, intensity, theory))
    return out.params['n'].value


def calculate_sq_raw(sample_spectrum, f_squared_mean, f_mean_squared, incoherent_scattering, normalization_factor,
                     extra_correction=0):
    """
    Calculates the structure factor of a material with the given parameters. Using the equation:

    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1

    where n is the normalization factor and f are the scattering factors.

    :param sample_spectrum:       background subtracted sample spectrum with A^-1 as x unit
    :param f_squared_mean:        <f^2>
    :param f_mean_squared:        <f>^2
    :param incoherent_scattering: compton scattering from sample
    :param normalization_factor:  previously calculated normalization factor

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

    :param sample_spectrum:     background subtracted sample spectrum with A^-1 as x unit
    :param density:             density of the sample in g/cm^3
    :param composition:         composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor:  attenuation factor used in the exponential for the calculation of the normalization
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
    """
    Performs a back Fourier transform from the pair distribution function g(r)

    :param gr_spectrum:     g(r) spectrum
    :param q:               numpy array of q values for which S(Q) should be calculated
    :param density:         density of the sample in g/cm^3
    :param composition:     composition as a dictionary with the elements as keys and the abundances as values
    :param use_modification_fcn:
        boolean flag whether to use the Lorch modification function

    :return: S(Q) spectrum
    """
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

    :param sq_spectrum:             Structure factor S(Q) with lim_inf S(Q) = 1 and unit(q)=A^-1
    :param r:                       numpy array giving the r-values for which F(r) will be calculated,
                                    default is 0 to 10 with 0.01 as a step. units should be in Angstrom.
    :param use_modification_fcn:    boolean flag whether to use the Lorch modification function

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

    :param fr_spectrum:     F(r) spectrum
    :param atomic_density:  atomic density in atoms/A^3

    :return: g(r) spectrum
    """
    r, f_r = fr_spectrum.data
    g_r = 1 + f_r / (4.0 * np.pi * r * atomic_density)
    return Spectrum(r, g_r)


def calculate_gr(fr_spectrum, density, composition):
    """
    Calculates a g(r) spectrum from a given F(r) spectrum, the material density and composition.

    :param fr_spectrum:     F(r) spectrum
    :param density:         density in g/cm^3
    :param composition:     composition as a dictionary with the elements as keys and the abundances as values

    :return: g(r) spectrum
    """
    return calculate_gr_raw(fr_spectrum, convert_density_to_atoms_per_cubic_angstrom(composition, density))

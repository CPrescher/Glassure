# -*- coding: utf-8 -*-
from typing import Optional
import numpy as np
import lmfit

from . import Pattern
from .utility import calculate_incoherent_scattering, calculate_f_squared_mean, calculate_f_mean_squared, \
    convert_density_to_atoms_per_cubic_angstrom

__all__ = ['calculate_normalization_factor_raw', 'calculate_normalization_factor', 'fit_normalization_factor',
           'calculate_sq', 'calculate_sq_raw', 'calculate_sq_from_fr', 'calculate_sq_from_gr',
           'calculate_fr', 'calculate_gr_raw', 'calculate_gr']


def calculate_normalization_factor_raw(sample_pattern: Pattern, atomic_density: float, f_squared_mean: np.ndarray,
                                       f_mean_squared: np.ndarray, incoherent_scattering: Optional[np.ndarray] = None,
                                       attenuation_factor: float = 0.001) -> float:
    """
    Calculates the normalization factor for a sample pattern given all the parameters. If you do not have them
    already calculated please consider using calculate_normalization_factor, which has an easier interface since it
    just requires density and composition as parameters.

    :param sample_pattern:     background subtracted sample pattern
    :param atomic_density:      density in atoms per cubic Angstrom
    :param f_squared_mean:      <f^2>
    :param f_mean_squared:      <f>^2
    :param incoherent_scattering: compton scattering from sample, if set to None, it will not be used
    :param attenuation_factor:  attenuation factor used in the exponential, in order to correct for the q cutoff

    :return:                    normalization factor
    """
    q, intensity = sample_pattern.data
    # calculate values for integrals
    if incoherent_scattering is None:
        incoherent_scattering = np.zeros_like(q)
    n1 = q ** 2 * ((f_squared_mean + incoherent_scattering) * np.exp(-attenuation_factor * q ** 2)) / f_mean_squared
    n2 = q ** 2 * intensity * np.exp(-attenuation_factor * q ** 2) / f_mean_squared

    n = ((-2 * np.pi ** 2 * atomic_density + np.trapz(q, n1)) / np.trapz(q, n2))

    return n


def calculate_normalization_factor(sample_pattern: Pattern, density: float, composition: dict[str, float],
                                   attenuation_factor: float = 0.001, use_incoherent_scattering: bool = True) -> float:
    """
    Calculates the normalization factor for a background subtracted sample pattern based on density and composition.

    :param sample_pattern:     background subtracted sample pattern with A-1 as x unit
    :param density:             density in g/cm^3
    :param composition:         composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor:  attenuation factor used in the exponential, in order to correct for the q cutoff
    :param use_incoherent_scattering: whether to use incoherent scattering, in some cases it is already subtracted

    :return: normalization factor
    """
    q, intensity = sample_pattern.data

    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    if use_incoherent_scattering:
        incoherent_scattering = calculate_incoherent_scattering(composition, q)
    else:
        incoherent_scattering = None
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)

    return calculate_normalization_factor_raw(sample_pattern, atomic_density, f_squared_mean, f_mean_squared,
                                              incoherent_scattering, attenuation_factor)


def fit_normalization_factor(sample_pattern: Pattern, composition: dict[str, float], q_cutoff: float = 3,
                             method: str = "squared", use_incoherent_scattering: bool = True,
                             sf_source: str = 'hajdu') -> float:
    """
    Estimates the normalization factor n for calculating S(Q) by fitting

        (Intensity*n-Multiple Scattering) * Q^2
    to
        (Incoherent Scattering + Self Scattering) * Q^2

    where n and Multiple Scattering are free parameters

    :param sample_pattern:      background subtracted sample pattern with A^-1 as x unit
    :param composition:         composition as a dictionary with the elements as keys and the abundances as values
    :param q_cutoff:            q value above which the fitting will be performed, default = 3
    :param method:              specifies whether q^2 ("squared") or q (linear) should be used
    :param use_incoherent_scattering:
                                whether to use incoherent scattering, in some cases it is already subtracted
    :param sf_source:           source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: normalization factor
    """
    q, intensity = sample_pattern.limit(q_cutoff, 100000).data

    if method == "squared":
        x = q ** 2
    elif method == "linear":
        x = q
    else:
        raise NotImplementedError("{} is not an allowed method for fit_normalization_factor".format(method))

    theory = calculate_f_squared_mean(composition, q, sf_source) * x
    if use_incoherent_scattering:
        theory += x * calculate_incoherent_scattering(composition, q, sf_source)

    params = lmfit.Parameters()
    params.add("n", value=1, min=0)
    params.add("multiple", value=1, min=0)

    def optimization_fcn(params, x, sample_intensity, theory_intensity):
        n = params['n'].value
        multiple = params['multiple'].value
        return ((sample_intensity * n - multiple) * x - theory_intensity) ** 2

    out = lmfit.minimize(optimization_fcn, params, args=(x, intensity, theory))
    return out.params['n'].value


def calculate_sq_raw(sample_pattern: Pattern, f_squared_mean: np.ndarray, f_mean_squared: np.ndarray,
                     incoherent_scattering: Optional[np.ndarray] = None, normalization_factor: float = 1,
                     method: str = 'FZ') -> Pattern:
    """
    Calculates the structure factor of a material with the given parameters. Using the equation:

    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1

    where n is the normalization factor and f are the scattering factors.

    :param sample_pattern:       background subtracted sample pattern with A^-1 as x unit
    :param f_squared_mean:        <f^2>
    :param f_mean_squared:        <f>^2
    :param incoherent_scattering: compton scattering from sample
    :param normalization_factor:  previously calculated normalization factor, if None, it will not be subtracted
    :param method:                describing the method to calculate the structure factor, possible values are
                                    - 'AL' - Ashcroft-Langreth
                                    - 'FZ' - Faber-Ziman

    :return: S(Q) pattern
    """
    q, intensity = sample_pattern.data
    if incoherent_scattering is None:
        incoherent_scattering = np.zeros_like(q)

    if method == 'FZ':
        sq = (normalization_factor * intensity - incoherent_scattering - f_squared_mean + f_mean_squared) / \
             f_mean_squared
    elif method == 'AL':
        sq = (normalization_factor * intensity - incoherent_scattering) / f_squared_mean
    else:
        raise NotImplementedError('{} method is not implemented'.format(method))
    return Pattern(q, sq)


def calculate_sq(sample_pattern: Pattern, density: float, composition: dict[str, float],
                 attenuation_factor: float = 0.001, method: str = 'FZ',
                 normalization_method: str = 'int', use_incoherent_scattering: bool = True,
                 sf_source: str = 'hajdu') -> Pattern:
    """
    Calculates the structure factor of a material with the given parameters. Using the equation:

    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1

    where n is the normalization factor and f are the scattering factors. All parameters from the equation are
    calculated from the density, composition and the sample pattern

    :param sample_pattern:      background subtracted sample pattern with A^-1 as x unit
    :param density:             density of the sample in g/cm^3
    :param composition:         composition as a dictionary with the elements as keys and the abundances as values
    :param attenuation_factor:  attenuation factor used in the exponential for the calculation of the normalization
                                factor

    :param method:              describing the method to calculate the structure factor, possible values are
                                    - 'AL' - Ashcroft-Langreth
                                    - 'FZ' - Faber-Ziman

    :param normalization_method: determines the method used for estimating the normalization method. possible values are
                                'int' for an integral or 'fit' for fitting the high q region form factors.

    :param use_incoherent_scattering: whether to use incoherent scattering, in some cases it is already subtracted
    :param sf_source:           source of the scattering factors. Possible sources are 'hajdu' and 'brown_hubbell'.

    :return: S(Q) pattern
    """
    q, intensity = sample_pattern.data
    f_squared_mean = calculate_f_squared_mean(composition, q, sf_source)
    f_mean_squared = calculate_f_mean_squared(composition, q, sf_source)
    if use_incoherent_scattering:
        incoherent_scattering = calculate_incoherent_scattering(composition, q, sf_source)
    else:
        incoherent_scattering = None

    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
    if normalization_method == 'fit':
        normalization_factor = fit_normalization_factor(sample_pattern,
                                                        composition,
                                                        use_incoherent_scattering,
                                                        sf_source=sf_source)
    else:
        normalization_factor = calculate_normalization_factor_raw(sample_pattern,
                                                                  atomic_density,
                                                                  f_squared_mean,
                                                                  f_mean_squared,
                                                                  incoherent_scattering,
                                                                  attenuation_factor)
    return calculate_sq_raw(sample_pattern,
                            f_squared_mean,
                            f_mean_squared,
                            incoherent_scattering,
                            normalization_factor,
                            method)


def calculate_fr(sq_pattern: Pattern, r: Optional[np.ndarray] = None, use_modification_fcn: bool = False,
                 method: str = 'integral') -> Pattern:
    """
    Calculates F(r) from a given S(Q) pattern for r values. If r is none a range from 0 to 10 with step 0.01 is used.
    A Lorch modification function of the form:

        m = sin(q*pi/q_max)/(q*pi/q_max)

    can be used to address issues with a low q_max. This will broaden the sharp peaks in g(r)

    :param sq_pattern:              Structure factor S(Q) with lim_inf S(Q) = 1 and unit(q)=A^-1
    :param r:                       numpy array giving the r-values for which F(r) will be calculated,
                                    default is 0 to 10 with 0.01 as a step. units should be in Angstrom.
    :param use_modification_fcn:    boolean flag whether to use the Lorch modification function
    :param method:                  determines the method used for calculating fr, possible values are:
                                            - 'integral' solves the Fourier integral, by calculating the integral
                                            - 'fft' solves the Fourier integral by using fast fourier transformation

    :return: F(r) pattern
    """
    if r is None:
        r = np.linspace(0, 10, 1001)

    q, sq = sq_pattern.data
    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1

    if method == 'integral':
        fr = 2.0 / np.pi * np.trapz(modification * q * (sq - 1) * np.array(np.sin(np.outer(q.T, r))).T, q)
    elif method == 'fft':
        q_step = q[1] - q[0]
        r_step = r[1] - r[0]

        n_out = np.max([len(q), int(np.pi / (r_step * q_step))])
        q_max_for_ifft = 2 * n_out * q_step
        y_for_ifft = np.concatenate((modification * q * (sq - 1), np.zeros(2 * n_out - len(q))))

        ifft_result = np.fft.ifft(y_for_ifft) * 2 / np.pi * q_max_for_ifft
        ifft_imag = np.imag(ifft_result)[:n_out]
        ifft_x_step = 2 * np.pi / q_max_for_ifft
        ifft_x = np.arange(n_out) * ifft_x_step

        fr = np.interp(r, ifft_x, ifft_imag)
    else:
        raise NotImplementedError("{} is not an allowed method for calculate_fr".format(method))
    return Pattern(r, fr)


def calculate_sq_from_fr(fr_pattern: Pattern, q: np.ndarray, method: str = 'integral') -> Pattern:
    """
    Calculates S(Q) from an F(r) pattern for given q values.

    :param fr_pattern:              input F(r) pattern
    :param q:                       numpy array giving the q-values for which S(q) will be calculated,
    :param method:                  determines the method use for calculating fr, possible values are:
                                            - 'integral' solves the Fourier integral, by calculating the integral
                                            - 'fft' solves the Fourier integral by using fast fourier transformation

    :return: F(r) pattern
    """
    r, fr = fr_pattern.data

    if method == 'integral':
        sq = np.trapz(fr * np.array(np.sin(np.outer(r.T, q))).T, r) / q + 1

    elif method == 'fft':
        q_step = q[1] - q[0]
        r_step = r[1] - r[0]

        n_out = int(np.pi / (r_step * q_step))

        r_max_for_ifft = 2 * n_out * r_step
        ifft_x_step = 2 * np.pi / r_max_for_ifft
        ifft_x = np.arange(n_out) * ifft_x_step

        y_for_ifft = np.concatenate((fr, np.zeros(2 * n_out - len(r))))
        ifft_result = np.fft.ifft(y_for_ifft) * r_max_for_ifft
        ifft_imag = np.imag(ifft_result)[:n_out]

        sq = np.interp(q, ifft_x, ifft_imag) / q + 1
    else:
        raise NotImplementedError("{} is not an allowed method for calculate_sq_from_fr".format(method))

    return Pattern(q, sq)


def calculate_sq_from_gr(gr_pattern: Pattern, q: np.ndarray, density: float, composition: dict[str, float],
                         method: str = 'integral') -> Pattern:
    """
    Performs a back Fourier transform from the pair distribution function g(r)

    :param gr_pattern:      g(r) pattern
    :param q:               numpy array of q values for which S(Q) should be calculated
    :param density:         density of the sample in g/cm^3
    :param composition:     composition as a dictionary with the elements as keys and the abundances as values
    :param method:          determines the method used for calculating fr, possible values are:
                                - 'integral' solves the Fourier integral, by calculating the integral
                                - 'fft' solves the Fourier integral by using fast fourier transformation

    :return: S(Q) pattern
    """
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
    r, gr = gr_pattern.data

    # removing the nan value at the first index, which is caused by the division by zero when r started from zero
    if np.isnan(gr[0]):
        gr[0] = 0
    fr_pattern = Pattern(r, (gr - 1) * (4.0 * np.pi * r * atomic_density))
    return calculate_sq_from_fr(fr_pattern, q, method)


def calculate_gr_raw(fr_pattern: Pattern, atomic_density: float) -> Pattern:
    """
    Calculates a g(r) pattern from a given F(r) pattern and the atomic density

    :param fr_pattern:     F(r) pattern
    :param atomic_density:  atomic density in atoms/A^3

    :return: g(r) pattern
    """
    r, f_r = fr_pattern.data
    g_r = 1 + f_r / (4.0 * np.pi * r * atomic_density)
    return Pattern(r, g_r)


def calculate_gr(fr_pattern: Pattern, density: float, composition: dict[str, float]) -> Pattern:
    """
    Calculates a g(r) pattern from a given F(r) pattern, the material density and composition.

    :param fr_pattern:     F(r) pattern
    :param density:         density in g/cm^3
    :param composition:     composition as a dictionary with the elements as keys and the abundances as values

    :return: g(r) pattern
    """
    return calculate_gr_raw(fr_pattern, convert_density_to_atoms_per_cubic_angstrom(composition, density))

from typing import Optional

import numpy as np
from scipy.integrate import simpson
from scipy.interpolate import interp1d

from .pattern import Pattern
from .methods import FourierTransformMethod


def calculate_sq(
    normalized_pattern: Pattern,
    f_squared_mean: np.ndarray,
    f_mean_squared: np.ndarray,
) -> Pattern:
    """
    Calculates the Faber Ziman structure factor, using the equation:
    S(Q) = (n * Intensity - incoherent_scattering - <f>^2-)/<f^2> + 1
    where n is the normalization factor and f are the scattering factors.
    The function takes in the already normalized intensity (incoherent scattering is also subtracted)

    :param normalized_pattern:    Pattern with q and (n * Intensity - incoherent scattering) as x and y
    :param f_squared_mean:        <f^2> - mean squared scattering factor for each q value in the pattern
    :param f_mean_squared:        <f>^2 - squared mean scattering factor for each q value in the pattern

    :return: S(Q) pattern
    """
    sq = (normalized_pattern.y - f_squared_mean + f_mean_squared) / f_mean_squared
    return Pattern(normalized_pattern.x, sq)


def calculate_fr(
    sq_pattern: Pattern,
    r: Optional[np.ndarray] = None,
    use_modification_fcn: bool = False,
    method: str = "integral",
) -> Pattern:
    """
    Calculates F(r) from a given S(Q) pattern for r values.
    If r is None, a range from 0 to 10 with step 0.01 is used.
    A Lorch modification function of the form:

        m = sin(q*pi/q_max)/(q*pi/q_max)

    can be used to address issues with a low q_max. This will broaden the sharp peaks in g(r)

    :param sq_pattern:              Structure factor S(Q) with lim_inf S(Q) = 1 and unit(q)=A^-1
    :param r:                       numpy array giving the r-values for which F(r) will be calculated,
                                    default is 0.01 to 10 with 0.01 as a step. units should be in Angstrom.
    :param use_modification_fcn:    boolean flag whether to use the Lorch modification function
    :param method:                  determines the method used for calculating fr, possible values are:
                                            - 'integral' solves the Fourier integral, by calculating the integral
                                            - 'fft' solves the Fourier integral by using fast fourier transformation

    :return: F(r) pattern
    """
    if r is None:
        r = np.arange(0.0, 10.005, 0.01)
        r[0] = 1e-10  # to avoid division by zero

    q, sq = sq_pattern.data
    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1

    if method == "integral" or method == FourierTransformMethod.INTEGRAL:
        fr = (
            2.0
            / np.pi
            * simpson(
                modification * q * (sq - 1) * np.array(np.sin(np.outer(q.T, r))).T, x=q
            )
        )
    elif method == "fft" or method == FourierTransformMethod.FFT:
        q_step = q[1] - q[0]
        r_step = r[1] - r[0]

        n_out = np.max([len(q), int(np.pi / (r_step * q_step))])
        n_out = 2 ** int(np.ceil(np.log2(n_out)))

        # find the number of q points needed to resolve the r-space
        q_max_target = 2 * np.pi / r_step
        n_target = int(np.ceil(q_max_target / q_step))

        # Round up to the next power of 2 for fastest possible fft
        n_out = 2 ** int(np.ceil(np.log2(n_target)))

        q_max_for_ifft = n_out * q_step

        f_q = modification * q * (sq - 1)
        y_for_ifft = np.zeros(n_out)
        y_for_ifft[: len(f_q)] = f_q

        ifft_result = np.fft.ifft(y_for_ifft) * 2 * q_max_for_ifft / np.pi
        ifft_imag = np.imag(ifft_result)[:n_out]
        ifft_x_step = 2 * np.pi / q_max_for_ifft
        ifft_x = np.arange(n_out) * ifft_x_step

        fr = np.interp(r, ifft_x, ifft_imag)
    else:
        raise NotImplementedError(
            "{} is not an allowed method for calculate_fr".format(method)
        )
    return Pattern(r, fr)


def calculate_sq_from_fr(
    fr_pattern: Pattern,
    q: Optional[np.ndarray] = None,
    method: str = "integral",
    use_modification_fcn: bool = False,
) -> Pattern:
    """
    Calculates S(Q) from an F(r) pattern for given q values.

    :param fr_pattern:              input F(r) pattern
    :param q:                       numpy array giving the q-values for which S(q) will be calculated,

    :return: F(r) pattern
    """
    if q is None:
        q = np.arange(0.0, 25.005, 0.05)
        q[0] = 1e-10  # to avoid division by zero

    r, fr = fr_pattern.data
    if method == "integral" or method == FourierTransformMethod.INTEGRAL:
        iq = simpson(fr * np.array(np.sin(np.outer(r.T, q))).T, x=r) 
    elif method == "fft" or method == FourierTransformMethod.FFT:
        r_step = r[1] - r[0]
        q_step = q[1] - q[0]

        n_out = max(len(r), int(np.pi / (q_step * r_step)))
        n_out = 2 ** int(np.ceil(np.log2(n_out)))

        fr_padded = np.zeros(n_out)
        fr_padded[: len(fr)] = fr

        r_max_for_ifft = n_out * r_step

        fft_result = np.fft.ifft(fr_padded) * r_max_for_ifft
        fft_imag = np.imag(fft_result)[:n_out]
        fft_q_step = 2 * np.pi / (n_out * r_step)
        fft_q = np.arange(n_out) * fft_q_step

        iq = np.interp(q, fft_q, fft_imag) 
    else:
        raise NotImplementedError(f"{method} is not a valid method for calculate_sq")

    if use_modification_fcn:
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
    else:
        modification = 1

    if use_modification_fcn:
        # when using the modification function we get issues at large q values, since it is very close to 0 there
        # we need to extrapolate a couple of points to avoid issues

        eps = 1e-9

        # find area where there is no problem with the modification function
        valid = modification * q > eps
        iq_new = np.empty_like(q)
        iq_new[:] = np.nan # initialize

        iq_new[valid] = iq[valid] / (q[valid] * modification[valid])

        # extrapolate the last few unstable points
        last_valid = np.where(valid)[0][-1]
        if last_valid < len(q) - 1:
            f = interp1d(q[valid], iq_new[valid], kind="linear", fill_value="extrapolate")
            iq_new[~valid] = f(q[~valid])

        sq = 1 + iq_new
    else:
        sq = 1 + iq/q

    return Pattern(q, sq)


def calculate_sq_from_gr(
    gr_pattern: Pattern,
    q: np.ndarray,
    atomic_density: float,
    method: str = "integral",
) -> Pattern:
    """
    Performs a back Fourier transform from the pair distribution function g(r)

    :param gr_pattern:      g(r) pattern
    :param q:               numpy array of q values for which S(Q) should be calculated
    :param atomic_density:  number_density in atoms/A^3

    :return: S(Q) pattern
    """
    r, gr = gr_pattern.data

    # removing the nan value at the first index, which is caused by the division by zero when r started from zero
    if np.isnan(gr[0]):
        gr[0] = 0
    fr_pattern = Pattern(r, (gr - 1) * (4.0 * np.pi * r * atomic_density))
    return calculate_sq_from_fr(fr_pattern, q)


def calculate_gr(fr_pattern: Pattern, atomic_density: float) -> Pattern:
    """
    Calculates a g(r) pattern from a given F(r) pattern and the atomic density

    :param fr_pattern:     F(r) pattern
    :param atomic_density:  atomic density in atoms/A^3

    :return: g(r) pattern
    """
    r, f_r = fr_pattern.data
    g_r = 1 + f_r / (4.0 * np.pi * r * atomic_density)
    return Pattern(r, g_r)

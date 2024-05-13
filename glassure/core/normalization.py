from typing import Optional

import numpy as np
import lmfit

from .pattern import Pattern
from .scattering_factors import calculate_incoherent_scattered_intensity


def normalize(
    sample_pattern: Pattern,
    atomic_density: float,
    f_squared_mean: np.ndarray,
    f_mean_squared: np.ndarray,
    incoherent_scattering: Optional[np.ndarray] = None,
    attenuation_factor: float = 0.001,
) -> tuple[float, Pattern]:
    """
    Normalizes the sample data (already background subtracted and corrected) to
    atomic units using the Kroegh-Moe-Norman integral normalization.

    :param sample_pattern:      background subtracted sample pattern
    :param atomic_density:      density in atoms per cubic Angstro
    :param f_squared_mean:      <f^2> - mean squared scattering factor
    :param f_mean_squared:      <f>^2 - squared mean scattering factor
    :param incoherent_scattering:
                                compton scattering from sample, if set to None, it will not be used
    :param attenuation_factor:  attenuation factor used in the exponential, in order to correct for the q cutoff

    :return:                    normalization factor, normalized Pattern (incoherent scattering already subtracted)
    """
    q, intensity = sample_pattern.data
    # calculate values for integrals
    if incoherent_scattering is None:
        incoherent_scattering = np.zeros_like(q)
    n1 = (
        q**2
        * (
            (f_squared_mean + incoherent_scattering)
            * np.exp(-attenuation_factor * q**2)
        )
        / f_mean_squared
    )
    n2 = q**2 * intensity * np.exp(-attenuation_factor * q**2) / f_mean_squared

    n = (-2 * np.pi**2 * atomic_density + np.trapz(q, n1)) / np.trapz(q, n2)

    return n, Pattern(q, n * intensity - incoherent_scattering)


def fit_normalization_factor(
    sample_pattern: Pattern,
    f_squared_mean: np.ndarray,
    incoherent_scattering: Optional[np.ndarray] = None,
    q_cutoff: float = 5,
    method: str = "linear",
    multiple_scattering: bool = False,
    correct_diamond: bool = False,
) -> tuple[lmfit.Parameters, Pattern]:
    """
    Estimates the normalization factor n for calculating S(Q) by fitting
        (Intensity*n-Multiple Scattering) * Q^2
    to
        (Incoherent Scattering + Self Scattering) * Q^2
    where n and Multiple Scattering are free parameters.

    :param sample_pattern:      background subtracted sample pattern with A^-1 as x unit
    :param incoherent_scattering:
                                compton scattering from sample, if set to None, it will not be used
                                array should contain values for each q-value of the sample pattern
    :param f_squared_mean:      <f^2> - mean squared scattering factor for each q-value of the
                                sample pattern
    :param q_cutoff:            q value above which the fitting will be performed, default = 4
    :param method:              specifies whether q^2 ("squared") or q (linear) should be used

    :return:    lmfit parameter object with the fitted parameters (n, multiple, n_diamond), normalized Pattern (incoherent scattering already subtracted)

    """
    q, intensity = sample_pattern.data
    q_ind = np.where(q > q_cutoff)

    q_cut = q[q_ind]
    intensity_cut = intensity[q_ind]

    # calculate values for integrals
    if incoherent_scattering is None:
        incoherent_scattering_cut = np.zeros_like(intensity)
    else:
        incoherent_scattering_cut = incoherent_scattering[q_ind]

    if method == "squared":
        scaling = q**2
    elif method == "linear":
        scaling = q
    else:
        raise NotImplementedError(
            "{} is not an allowed method for fit_normalization_factor".format(method)
        )

    params = lmfit.Parameters()
    params.add("n", value=1, min=0)

    if multiple_scattering:
        params.add("multiple", value=0, min=0)
    else:
        params.add("multiple", value=0, vary=False)

    if correct_diamond:
        params.add("n_diamond", value=10, min=0)
        diamond_compton = calculate_incoherent_scattered_intensity("C", q)
    else:
        params.add("n_diamond", value=0, vary=False)
        diamond_compton = 0

    def optimization_fcn(params):
        n = params["n"].value
        multiple = params["multiple"].value
        if correct_diamond:
            n_diamond = params["n_diamond"].value
            compton = incoherent_scattering_cut + diamond_compton * n_diamond
        else:
            compton = incoherent_scattering_cut

        theory = f_squared_mean[q_ind] + compton

        return ((n * intensity_cut - multiple - compton - theory) * scaling) ** 2

    out = lmfit.minimize(optimization_fcn, params)

    # prepare final output
    q_out = sample_pattern.x
    compton_out = incoherent_scattering + diamond_compton * out.params["n_diamond"].value
    intensity_out = out.params["n"].value * sample_pattern.y - out.params["multiple"].value - compton_out

    return out.params, Pattern(q_out, intensity_out - compton_out) 

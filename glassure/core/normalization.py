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
    atomic units using the Kroegh-Moe-Norman integral normalization. The normalization
    is performed for the the Faber-Ziman structure factor.

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


def normalize_fit(
    sample_pattern: Pattern,
    f_squared_mean: np.ndarray,
    incoherent_scattering: Optional[np.ndarray] = None,
    q_cutoff: float = 3,
    method: str = "squared",
    multiple_scattering: bool = False,
    container_scattering: Optional[np.ndarray] = None,
) -> tuple[lmfit.Parameters, Pattern]:
    """
    Estimates the normalization factor n for calculating S(Q) by fitting
        (Intensity*n-Multiple Scattering)
    to
        (Incoherent Scattering + Self Scattering)
    where n and Multiple Scattering are free parameters.

    :param sample_pattern:      background subtracted sample pattern with A^-1 as x unit
    :param incoherent_scattering:
                                compton scattering from sample, if set to None, it will not be used
                                array should contain values for each q-value of the sample pattern
    :param f_squared_mean:      <f^2> - mean squared scattering factor for each q-value of the
                                sample pattern
    :param q_cutoff:            q value above which the fitting will be performed, default = 4
    :param method:              specifies whether q^2 ("squared") or q (linear) should be used for
                                scaling the fit, this ensures that higher q values are weighted more
    :multiple_scattering:       flag whether multiple scattering should be included in the fit - the
                                current implementation is just to remove a constant value from the
                                input data
    :container_scattering:      extra scattering from the container, if set to None, it will not be used.
                                Example usecase is extra diamond compton scattering contribution, which
                                will increase with pressure in soller slit diamond anvil experiments.
                                The amount of this extra scattering contribution will be fitted and output
                                as a separate parameter n_container in the result. Length of the array should
                                be the same as the length of the sample pattern. Any corrections to this
                                scattering should be done before calling this function (e.g. Klein-Nishima
                                correction)

    :return:    lmfit parameter object with the fitted parameters (n, multiple, n_countainer),
                normalized Pattern (incoherent scattering already subtracted)

    """
    q, intensity = sample_pattern.data
    q_ind = np.where(q > q_cutoff)[0]

    q_cut = q[q_ind]
    intensity_cut = intensity[q_ind]

    assert len(q_cut) > 0, "No q values above the cutoff value"
    assert len(f_squared_mean) == len(
        q
    ), """f_squared_mean should have the same length as the
        sample pattern"""

    f_squared_mean_cut = f_squared_mean[q_ind]

    # calculate values for integrals
    if incoherent_scattering is None:
        incoherent_scattering_cut = 0
    else:
        assert len(incoherent_scattering) == len(
            q
        ), """incoherent scattering should have the same length as the
        sample pattern"""

        incoherent_scattering_cut = incoherent_scattering[q_ind]

    if method == "squared":
        scaling = q_cut**2
    elif method == "linear":
        scaling = q_cut
    else:
        raise NotImplementedError(
            "{} is not an allowed method for fit_normalization_factor".format(method)
        )

    # prepare lmfit parameters
    params = lmfit.Parameters()
    params.add("n", value=1, min=0)

    if multiple_scattering:
        params.add("multiple", value=1, min=0)
    else:
        params.add("multiple", value=0, vary=False)

    if container_scattering is not None:
        assert len(container_scattering) == len(
            q
        ), """container scattering should have the same length as the sample pattern"""
        params.add("n_container", value=10, min=0)
        container_contribution = container_scattering
        container_contribution_cut = container_contribution[q_ind]
    else:
        params.add("n_container", value=0, vary=False)
        container_contribution = 0
        container_contribution_cut = 0

    def optimization_fcn(params):
        n = params["n"].value
        multiple = params["multiple"].value
        n_container = params["n_container"].value
        if container_scattering is not None:
            compton = (
                incoherent_scattering_cut + container_contribution_cut * n_container
            )
        else:
            compton = incoherent_scattering_cut

        theory = f_squared_mean_cut + compton
        return ((n * intensity_cut - multiple - theory) * scaling) ** 2

    out = lmfit.minimize(optimization_fcn, params)

    # prepare final output
    q_out = sample_pattern.x
    compton_out = (
        incoherent_scattering + container_contribution * out.params["n_container"].value
    )
    intensity_out = (
        out.params["n"].value * intensity - out.params["multiple"].value - compton_out
    )

    return out.params, Pattern(q_out, intensity_out)

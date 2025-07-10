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


def normalize_fit_lmfit(
    sample_pattern: Pattern,
    f_squared_mean: np.ndarray,
    incoherent_scattering: Optional[np.ndarray] = None,
    q_cutoff: float = 3,
    method: str = "squared",
    multiple_scattering: bool = False,
    container_scattering: Optional[np.ndarray] = None,
) -> tuple[lmfit.Parameters, Pattern]:
    """
    This function is deprecated and will be removed in the future. It is replaced by a new
    implementation that uses the least squares problem to solve for the normalization factor.
    The new implementation is more efficient and more accurate. In the simplest case with no
    multiple scattering or container scattering, it is 100 times faster than the old implementation.

    Estimates the normalization factor n for calculating S(Q) by fitting
        (Intensity*n-Multiple Scattering-Container Scattering*m)
    to
        (Incoherent Scattering + Self Scattering)
    where n, m and Multiple Scattering are free parameters. It uses lmfit to solve the least squares
    problem.

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
        incoherent_scattering = 0
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


def normalize_fit(
    sample_pattern: Pattern,
    f_squared_mean: np.ndarray,
    incoherent_scattering: Optional[np.ndarray] = None,
    q_cutoff: float = 3,
    method: str = "squared",
    multiple_scattering: bool = False,
    container_scattering: Optional[np.ndarray] = None,
) -> tuple[dict, Pattern]:
    """
    Estimates the normalization factor n for calculating S(Q) by solving the linear least squares problem
        (Intensity*n-Multiple Scattering-Container Scattering*m) = (Incoherent Scattering + Self Scattering)
    where n, m and Multiple Scattering are free parameters.
    The solution is found by solving the normal equations.

    :param sample_pattern:      background subtracted sample pattern with A^-1 as x unit
    :param f_squared_mean:      <f^2> - mean squared scattering factor for each q-value of the
                                sample pattern
    :param incoherent_scattering:
                                compton scattering from sample, if set to None, it will not be used
                                array should contain values for each q-value of the sample pattern
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

    :return:    dictionary with the fitted parameters (n, multiple, n_countainer),
                normalized Pattern (incoherent scattering already subtracted)
    """
    q, intensity = sample_pattern.data
    q_ind = np.where(q > q_cutoff)[0]

    q_cut = q[q_ind]
    intensity_cut = intensity[q_ind]
    f_squared_mean_cut = f_squared_mean[q_ind]

    assert len(q_cut) > 0, "No q values above the cutoff value"
    assert len(f_squared_mean) == len(q), "f_squared_mean must match q length"

    # Handle incoherent scattering
    if incoherent_scattering is None:
        incoherent_scattering = np.zeros_like(q)
        incoherent_cut = np.zeros_like(intensity_cut)
    else:
        assert len(incoherent_scattering) == len(q)
        incoherent_cut = incoherent_scattering[q_ind]

    # Set scaling weights
    if method == "squared":
        q_scaling = q_cut**2
    elif method == "linear":
        q_scaling = q_cut
    else:
        raise NotImplementedError(f"{method} is not a valid method")

    if not multiple_scattering and container_scattering is None:
        # If this is the case we can use a simpler solution, using the dot product
        # of the intensity and the f_squared_mean + incoherent scattering (which is
        # the objective function that we are fitting to)
        y = intensity_cut * q_scaling
        f = (f_squared_mean_cut + incoherent_cut) * q_scaling
        n = np.dot(y, f) / np.dot(y, y)

        result = {
            "n": n,
            "multiple": 0,
            "n_container": 0,
        }
        intensity_out = n * intensity - incoherent_scattering

        return result, Pattern(q, intensity_out)

    # If we have multiple scattering or container scattering, we need to use the lstsq solution
    # Build design matrix X (columns: intensity, container, constant)

    # Handle container scattering
    if container_scattering is not None:
        assert len(container_scattering) == len(q)
        container_cut = container_scattering[q_ind]
    else:
        container_cut = np.zeros_like(intensity_cut)

    # Compute scaling factors for normalization
    scale_intensity = np.max(np.abs(intensity_cut)) or 1.0
    scale_container = np.max(np.abs(container_cut)) or 1.0

    # Apply scaling to predictors
    X_cols = [
        intensity_cut / scale_intensity,  # for n
        container_cut / scale_container,  # for n_container
        np.ones_like(intensity_cut),  # for multiple (constant)
    ]
    if not multiple_scattering:
        X_cols[2] = np.zeros_like(intensity_cut)

    X = np.column_stack([col * q_scaling for col in X_cols])
    y = (f_squared_mean_cut + incoherent_cut) * q_scaling

    # Solve scaled least squares
    result = np.linalg.lstsq(X, y, rcond=None)
    coeffs = result[0]

    # Rescale coefficients back to physical values
    n = coeffs[0] / scale_intensity
    n_container = -coeffs[1] / scale_container
    multiple = -coeffs[2]
    # n_container and multiple are negative values, since the matrix lstsq solution
    # is assuming they are additive to the intensity (but of course we are later subtracting them).
    # This is why we need to negate them here.

    # Build normalized intensity
    compton_out = incoherent_scattering

    if container_scattering is not None:
        compton_out += container_scattering * n_container

    intensity_out = n * intensity - multiple - compton_out

    result = {
        "n": n,
        "n_container": n_container,
        "multiple": multiple,
    }

    return result, Pattern(q, intensity_out)

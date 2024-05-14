# -*- coding: utf-8 -*-

from copy import deepcopy

import numpy as np
import lmfit

from . import Pattern
from .transform import calculate_fr, calculate_gr, calculate_sq
from .normalization import normalize_fit, normalize
from .utility import (
    convert_density_to_atoms_per_cubic_angstrom,
)
from .utility import extrapolate_to_zero_poly

__all__ = [
    "optimize_sq",
    "optimize_density",
]


def optimize_sq(
    sq_pattern: Pattern,
    r_cutoff: float,
    iterations: int,
    atomic_density: float,
    use_modification_fcn: bool = False,
    attenuation_factor: float = 1,
    fcn_callback=None,
    callback_period: int = 2,
    fourier_transform_method: str = "fft",
):
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
        Whether to use the Lorch modification function during the Fourier transform.
        Warning: When using the Lorch modification function, usually more iterations are needed to get to the
        wanted result.
    :param attenuation_factor:
        Sometimes the initial change during back and forward transformations results in a runaway, by setting the
        attenuation factor reduces the amount of change during each iteration.
    :param fcn_callback:
        Function which will be called at an iteration period defined by the callback_period parameter.
        The function should take three arguments: sq_pattern, fr_pattern and gr_pattern.
        Additionally, the function should return a boolean value, where True continues the optimization and False will
        stop the optimization.
    :param callback_period:
        determines how frequently the fcn_callback will be called.
    :param fourier_transform_method:
        determines which method will be used for the Fourier transform. Possible values are 'fft' and 'integral'

    :return:
        optimized S(Q) pattern
    """
    r = np.arange(0, r_cutoff, 0.02)
    sq_pattern = deepcopy(sq_pattern)
    for iteration in range(iterations):
        fr_pattern = calculate_fr(
            sq_pattern, r, use_modification_fcn, method=fourier_transform_method
        )
        q, sq_int = sq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * atomic_density

        in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
        integral = np.trapz(in_integral, r) / attenuation_factor
        sq_optimized = sq_int * (1 - 1.0 / q * integral)

        sq_pattern = Pattern(q, sq_optimized)

        if fcn_callback is not None and iteration % callback_period == 0:
            fr_pattern = calculate_fr(
                sq_pattern,
                use_modification_fcn=use_modification_fcn,
                method=fourier_transform_method,
            )
            gr_pattern = calculate_gr(fr_pattern, atomic_density)
            fcn_callback(sq_pattern, fr_pattern, gr_pattern)
    return sq_pattern


def optimize_density(
    data_pattern,
    background_pattern,
    initial_background_scaling,
    composition,
    initial_density,
    background_min,
    background_max,
    density_min,
    density_max,
    iterations,
    r_cutoff,
    use_modification_fcn=False,
    extrapolation_cutoff=None,
    r_step=0.01,
    fcn_callback=None,
):
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
                                Whether to use the Lorch modification function during the Fourier transform.
                                Warning: When using the Lorch modification function, more iterations are needed
                                to get to the wanted result.
    :param extrapolation_cutoff:
                                Determines up to which q value the S(Q) will be extrapolated to zero. The default
                                (None) will use the minimum q value plus 0.2 A^-1
    :param r_step:              Step size for the r-space for calculating f(r) during each iteration.
    :param fcn_callback:        Function which will be called after each iteration. The function should take four
                                arguments: iteration number, chi2, density, and background scaling. Additionally, the
                                function should return a boolean value, where True continues the optimization and False
                                will stop the optimization procedure

    :return: (tuple) - density, density standard error, background scaling, background scaling standard error
    """
    params = lmfit.Parameters()
    params.add("density", value=initial_density, min=density_min, max=density_max)
    params.add(
        "background_scaling",
        value=initial_background_scaling,
        min=background_min,
        max=background_max,
    )

    r = np.arange(0, r_cutoff + r_step / 2.0, r_step)

    def optimization_fcn(params, extrapolation_max, r, r_cutoff, use_modification_fcn):
        density = params["density"].value
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(
            composition, density
        )
        background_pattern.scaling = params["background_scaling"].value

        sq = calculate_sq(data_pattern - background_pattern, density, composition)
        extrapolation_max = extrapolation_max or np.min(sq._x[0]) + 0.2
        sq = extrapolate_to_zero_poly(sq, extrapolation_max)
        sq_optimized = optimize_sq(
            sq, r_cutoff, iterations, atomic_density, use_modification_fcn
        )
        fr = calculate_fr(sq_optimized, r=r, use_modification_fcn=use_modification_fcn)

        min_r, min_fr = fr.data

        output = (min_fr + 4 * np.pi * atomic_density * min_r) ** 2 * r_step

        if fcn_callback is not None:
            if not fcn_callback(
                optimization_fcn.iteration,
                np.sum(output),
                density,
                params["background_scaling"].value,
            ):
                return None
        optimization_fcn.iteration += 1
        return output

    optimization_fcn.iteration = 1

    lmfit.minimize(
        optimization_fcn,
        params,
        args=(extrapolation_cutoff, r, r_cutoff, use_modification_fcn),
    )
    lmfit.report_fit(params)

    return (
        params["density"].value,
        params["density"].stderr,
        params["background_scaling"].value,
        params["background_scaling"].stderr,
    )
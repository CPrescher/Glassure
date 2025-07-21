# -*- coding: utf-8 -*-

from copy import deepcopy
from typing import Optional

import numpy as np
from scipy.integrate import simpson
from lmfit import Parameters, minimize

from . import Pattern
from .transform import calculate_fr, calculate_gr, calculate_sq_from_fr

__all__ = [
    "optimize_sq",
    "optimize_density",
]


def optimize_sq(
    sq_pattern: Pattern,
    r_cutoff: float,
    iterations: int,
    atomic_density: float,
    r_step: float = 0.01,
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
    :param r_step:
        step size for the r-axis, default is 0.01. Use smaller values for better accuracy (especially if needed for
         fft)
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
    r = np.arange(0, r_cutoff, r_step)
    sq_pattern = deepcopy(sq_pattern)
    for iteration in range(iterations):
        fr_pattern = calculate_fr(
            sq_pattern, r, use_modification_fcn, method=fourier_transform_method
        )
        q, sq_int = sq_pattern.data
        r, fr_int = fr_pattern.data

        delta_fr = fr_int + 4 * np.pi * r * atomic_density

        if fourier_transform_method == "fft":
            sq_trans_fft = (
                calculate_sq_from_fr(Pattern(r, delta_fr), sq_pattern.x, method="fft")
                - 1
            )
            iq = sq_trans_fft.y
        else:
            in_integral = np.array(np.sin(np.outer(q.T, r))) * delta_fr
            iq = np.trapz(in_integral, r) / q

        sq_pattern = sq_pattern * (1 - iq / attenuation_factor)

        if fcn_callback is not None and iteration % callback_period == 0:
            fr_pattern = calculate_fr(
                sq_pattern,
                use_modification_fcn=use_modification_fcn,
                method=fourier_transform_method,
            )
            gr_pattern = calculate_gr(fr_pattern, atomic_density)
            fcn_callback(sq_pattern, fr_pattern, gr_pattern)
    return sq_pattern


from .calc import calculate_pdf
from .configuration import DataConfig, CalculationConfig
from .methods import ExtrapolationMethod


def optimize_density(
    data_config: DataConfig,
    calculation_config: CalculationConfig,
    method: str = "fr",
    min_range: Optional[tuple[float, float]] = None,
    vary_bkg_scaling: bool = True,
    bkg_limits: tuple[float, float] = (0.9, 1.1),
    optimization_method: str = "lsq",
) -> tuple[float, float, float, float]:
    """
    Optimizes the density of the sample using the g(r), f(r) or S(Q) (chosen by the method parameter).
    The density in the SampleConfig of the DataConfig is taking as starting parameter

    For method='gr' or method='fr' the optimization is based on the g(r) or f(r) function, and the density is
    optimized to minimize the low g(r) or f(r) region to be close to zero. For better results, the g(r) function
    is calculated with the Lorch modification function. The general procedure is explained in
    Eggert et al. 2002 PRB, 65, 174105.

    For method='sq' the optimization is based on the low Q part of the S(Q) function, and the density is optimized
    to minimize the difference between the original S(Q) function without any optimization and the optimized S(Q)
    function. The configuration should have extrapolation enabled for this to work best.
    For polyatomic systems, finding the density using this procedure is much less susceptible to the Q_max value of
    the S(Q) than the g(r) based optimization. However, density is not exactly the same for both methods and the
    method needs to be verified further. (Please us the method='sq' with caution.)

    The best for both types is to have a reference density to compare it to. Based on this then further calculations
    of e.g. high pressure or high temperature densities can be performed.

    For this procedure to work best, the S(Q) optimization should be enabled in the calculation configuration. The
    chosen parameters are then used in the find density function.

    example usage:
    ```
    from glassure.calc import create_calculate_pdf_configs
    from glassure.optimization import optimize_density

    data_config, calculation_config = create_calculate_pdf_configs(data, composition, density, background)
    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density, density_error, bkg_scaling, bkg_error = optimize_density(data_config, calculation_config, method='gr', range=(0.1, 1.2))
    ```

    :param data_config:
        Data configuration
    :param calculation_config:
        Calculation configuration
    :param method:
        Method to use for the optimization. Possible values are 'gr', 'fr' and 'sq'.
    :param min_range:
        x range of the data to use for the minimization to find the density. For method='gr' and 'fr this is the
        r-range of the g(r)/f(r) function to minimize. For method='sq' this is the Q-range of the S(Q) function to
        minimize the difference between the original and optimized S(Q) function. Default is None which means that
        the range is (0, calculation_config.optimize.r_cutoff) for method='gr' and 'fr' and
        (0, calculation_config.transform.q_max) for method='sq'.
    :param vary_bkg_scaling:
        Whether to vary the background scaling during the optimization. Default is True.
    :param bkg_limits:
        relative limits for the background scaling. The background scaling is optimized to be within these limits.
        Default is (0.9, 1.1) which means that the background scaling is optimized to be within 10% of the starting
        value.
    :param optimization_method:
        Method to use for the optimization. Possible values are 'nelder' and 'lsq'.

    :return:
        a tuple with four values:
        - the density,  its error value, the background scaling and the error value
        whereby the error value is the standard error of the fit parameter for optimization_method ='lsq' and the
        sum of the squared residuals for optimization_method='nelder'.
    """

    if calculation_config.optimize is None and min_range is None and not method == "sq":
        raise ValueError(
            "For optimizing density using 'gr' or 'fr' the calculation configuration needs to have the "
            "optimize configuration or the min_range parameter needs to be set."
        )

    params = Parameters()
    params.add("density", value=calculation_config.sample.density, min=0.0, max=100)
    params.add(
        "bkg_scaling",
        value=data_config.bkg_scaling,
        min=data_config.bkg_scaling * bkg_limits[0],
        max=data_config.bkg_scaling * bkg_limits[1],
        vary=vary_bkg_scaling,
    )

    optim_config = calculation_config.model_copy(deep=True)
    optim_config.transform.use_modification_fcn = False

    if method == "sq":
        reference_config = calculation_config.model_copy(deep=True)
        reference_config.optimize = None
        reference_result = calculate_pdf(data_config, reference_config)
        if min_range is None:
            min_range = (0, reference_config.transform.q_max)

    elif method == "gr" or method == "fr":
        if min_range is None:
            min_range = (0, optim_config.optimize.r_cutoff)

    def fcn(params):
        density = params["density"].value
        bkg_scaling = params["bkg_scaling"].value
        optim_config.sample.density = density
        data_config.bkg_scaling = bkg_scaling
        result = calculate_pdf(data_config, optim_config)

        if method == "gr":
            r, gr = result.gr.limit(*min_range).data
            residual = gr * (r[1] - r[0])
        elif method == "fr":
            atomic_density = optim_config.sample.atomic_density
            r, fr = result.fr.limit(*min_range).data
            residual = (fr + 4 * np.pi * r * atomic_density) * (r[1] - r[0])
        elif method == "sq":
            q, sq = result.sq.limit(*min_range).data
            sq_ref = reference_result.sq.limit(*min_range).y
            residual = (sq - sq_ref) * (q[1] - q[0])
        else:
            raise ValueError(
                f"Invalid optimize density method: {method}, only 'gr', 'fr' and 'sq' are supported."
            )
        return residual

    if optimization_method == "nelder":
        res = minimize(
            fcn,
            params,
            method="nelder",
            options={"maxfev": 500, "fatol": 0.0001, "xatol": 0.0001},
        )
        return (
            res.params["density"].value,
            np.sum(res.residual**2),
            res.params["bkg_scaling"].value,
            np.sum(res.residual**2),
        )
    elif optimization_method == "lsq":
        res = minimize(
            fcn,
            params,
            method="least_squares",
        )
        return (
            res.params["density"].value,
            res.params["density"].stderr,
            res.params["bkg_scaling"].value,
            res.params["bkg_scaling"].stderr,
        )
    else:
        raise ValueError(f"Invalid optimization method: {optimization_method}")

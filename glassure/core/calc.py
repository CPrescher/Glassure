import numpy as np

from .configuration import Input, Result, FitNormalization, IntNormalization
from .pattern import Pattern
from .methods import NormalizationMethod, ExtrapolationMethod
from .normalization import normalize, normalize_fit
from .optimization import optimize_sq
from .transform import calculate_sq, calculate_fr, calculate_gr
from .utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    calculate_s0,
    extrapolate_to_zero_linear,
    extrapolate_to_zero_poly,
    extrapolate_to_zero_spline,
)


def process_input(input: Input) -> Pattern:
    """
    Process the input configuration and return the result.
    """

    # create some shortcuts
    config = input.config
    transform = config.transform
    composition = config.sample.composition

    # subtract background
    if input.bkg is not None:
        sample = input.data - input.bkg * input.bkg_scaling
    else:
        sample = input.data

    # limit the pattern
    sample = sample.limit(transform.q_min, transform.q_max)

    # calculate form factor values
    q = sample.x
    f_squared_mean = calculate_f_squared_mean(composition, q)
    f_mean_squared = calculate_f_mean_squared(composition, q)
    incoherent_scattering = calculate_incoherent_scattering(composition, q)

    # normalization
    if isinstance(transform.normalization, FitNormalization):
        opt = transform.normalization
        assert isinstance(opt, FitNormalization), (
            "Normalization config must be of type FitNormalizationConfig "
            + "when normalization method is set to 'fit'."
        )

        if opt.container_scattering is not None:
            container_scattering = calculate_incoherent_scattering(
                opt.container_scattering, q
            )
        else:
            container_scattering = None

        norm_inc = incoherent_scattering if opt.incoherent_scattering else None

        params, norm = normalize_fit(
            sample_pattern=sample,
            f_squared_mean=f_squared_mean,
            incoherent_scattering=norm_inc,
            q_cutoff=opt.q_cutoff,
            method=opt.method,
            multiple_scattering=opt.multiple_scattering,
            container_scattering=container_scattering,
        )
    elif isinstance(transform.normalization, IntNormalization):
        opt = transform.normalization
        norm_inc = incoherent_scattering if opt.incoherent_scattering else None

        n, norm = normalize(
            sample_pattern=sample,
            atomic_density=input.config.sample.atomic_density,
            f_squared_mean=f_squared_mean,
            f_mean_squared=f_mean_squared,
            incoherent_scattering=norm_inc,
            attenuation_factor=opt.attenuation_factor,
        )

    else:
        raise NotImplementedError(
            "Only the FitNormalization and IntNormalizationnormalization methods are implemented at the moment."
        )

    # transform the pattern to S(Q)
    sq = calculate_sq(norm, f_squared_mean, f_mean_squared)

    # extrapolation
    s0 = calculate_s0(composition)
    extrapolation = transform.extrapolation_config
    match extrapolation.method:
        case ExtrapolationMethod.STEP:
            sq = sq.extend_to(0, s0)

        case ExtrapolationMethod.LINEAR:
            sq = extrapolate_to_zero_linear(sq, y0=s0)

        case ExtrapolationMethod.SPLINE:
            sq_cutoff = sq.x[0] + extrapolation.overlap
            sq = extrapolate_to_zero_spline(
                sq,
                x_max=sq_cutoff,
                y0=s0,
                replace=extrapolation.replace,
            )

        case ExtrapolationMethod.POLY:
            sq_cutoff = sq.x[0] + 0.21
            sq = extrapolate_to_zero_poly(
                sq,
                x_max=sq_cutoff,
                y0=s0,
                replace=extrapolation.replace,
            )

        case _:
            raise NotImplementedError(
                f"Extrapolation method {extrapolation.method} not implemented."
            )

    # Kaplow optimization
    if config.optimize is not None:
        opt = config.optimize
        sq = optimize_sq(
            sq,
            atomic_density=config.sample.atomic_density,
            r_cutoff=opt.r_cutoff,
            iterations=opt.iterations,
            use_modification_fcn=opt.use_modification_fcn,
        )

    fr = calculate_fr(
        sq,
        use_modification_fcn=transform.use_modification_fcn,
        method=transform.fourier_transform_method,
        r=np.arange(
            transform.r_min,
            transform.r_max + transform.r_step * 0.5,
            transform.r_step,
        ),
    )

    gr = calculate_gr(
        fr,
        atomic_density=input.config.sample.atomic_density,
    )

    res = Result(
        input=input,
        sq=sq,
        fr=fr,
        gr=gr,
    )

    return res

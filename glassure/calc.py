import numpy as np

from .configuration import (
    Result,
    FitNormalization,
    IntNormalization,
    SampleConfig,
    DataConfig,
    CalculationConfig,
    Composition,
)
from .pattern import Pattern
from .methods import ExtrapolationMethod
from .normalization import normalize, normalize_fit
from .optimization import optimize_sq
from .transform import calculate_sq, calculate_fr, calculate_gr
from .utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    calculate_s0,
    calculate_kn_correction,
    extrapolate_to_zero_linear,
    extrapolate_to_zero_poly,
    extrapolate_to_zero_spline,
)

# only export functions inside of this file
__all__ = [
    "create_calculate_pdf_configs",
    "calculate_pdf",
    "validate_input",
]


def create_calculate_pdf_configs(
    data: Pattern,
    composition: Composition,
    density: float,
    bkg: Pattern = None,
    bkg_scaling: float = 1,
) -> tuple[DataConfig, CalculationConfig]:
    """
    Helper function to create a starting glassure input configuration.
    Automatically sets the q_min and q_max values to the first and last
    x-value of the data pattern - thus, the whole pattern gets transformed,
    when using this configuration.

    These two inputs can then be used with the *calculate_pdf* function in the calc module
    to calculate the structure factor S(q), the pair distribution function F(r) and
    the pair correlation function g(r).

    :param data: The data pattern.
    :param composition: The composition of the sample.
    :param density: The density of the sample in g/cm^3.
    :param bkg: The background pattern. None if no background is present.
    :param bkg_scaling: The scaling factor for the background pattern.

    :return: DataConfig, CalculationConfig
    """
    sample_config = SampleConfig(composition=composition, density=density)
    calculation_config = CalculationConfig(sample=sample_config)
    calculation_config.transform.q_min = data.x[0]
    calculation_config.transform.q_max = data.x[-1]

    data_config = DataConfig(data=data, bkg=bkg, bkg_scaling=bkg_scaling)
    return data_config, calculation_config


def calculate_pdf(
    data_config: DataConfig, calculation_config: CalculationConfig
) -> Pattern:
    """
    Process the input configuration and return the result.
    """
    validate_input(data_config, calculation_config)

    # create some shortcuts
    config = calculation_config
    transform = config.transform
    composition = config.sample.composition

    # subtract background
    if data_config.bkg is not None:
        sample = data_config.data - data_config.bkg * data_config.bkg_scaling
    else:
        sample = data_config.data

    # limit the pattern
    sample = sample.limit(transform.q_min, transform.q_max)

    # calculate form factor values
    q = sample.x
    f_squared_mean = calculate_f_squared_mean(
        composition, q, transform.scattering_factor_source
    )
    f_mean_squared = calculate_f_mean_squared(
        composition, q, transform.scattering_factor_source
    )
    incoherent_scattering = calculate_incoherent_scattering(
        composition, q, transform.scattering_factor_source
    )

    # klein-nishina correction
    if transform.kn_correction:
        if transform.wavelength is None:
            raise ValueError(
                "Wavelength must be set when using the Klein-Nishina correction."
            )
        inc_correction = calculate_kn_correction(q, transform.wavelength)
    else:
        inc_correction = 1

    # normalization
    if isinstance(transform.normalization, FitNormalization):
        opt = transform.normalization
        assert isinstance(opt, FitNormalization), (
            "Normalization config must be of type FitNormalizationConfig "
            + "when normalization method is set to 'fit'."
        )

        if opt.container_scattering is not None:
            container_scattering = (
                calculate_incoherent_scattering(
                    opt.container_scattering, q, transform.scattering_factor_source
                )
                * inc_correction
            )
        else:
            container_scattering = None

        norm_inc = (
            incoherent_scattering * inc_correction
            if opt.incoherent_scattering
            else None
        )

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
            atomic_density=config.sample.atomic_density,
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
    if config.transform.extrapolation.s0 is not None:
        s0 = config.transform.extrapolation.s0
    else:
        s0 = calculate_s0(composition, transform.scattering_factor_source)

    extrapolation = transform.extrapolation
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
            sq_cutoff = sq.x[0] + extrapolation.overlap
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
        atomic_density=config.sample.atomic_density,
    )

    res = Result(
        calculation_config=config.model_copy(deep=True),
        sq=sq,
        fr=fr,
        gr=gr,
    )

    return res


def validate_input(data_config: DataConfig, calculation_config: CalculationConfig):
    """
    Validate the input configuration.
    """
    if data_config.data is None or not isinstance(data_config.data, Pattern):
        raise ValueError("Input data must be a Pattern object.")
    if data_config.bkg is not None and not isinstance(data_config.bkg, Pattern):
        raise ValueError("Background data must be a Pattern object.")

    if not calculation_config.sample.composition:  # empty composition dict
        raise ValueError("Composition must be set.")

    if not calculation_config.sample.atomic_density:
        raise ValueError("Atomic density must be set.")

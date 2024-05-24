# -*- coding: utf-8 -*/:

from typing import Optional, Literal
from pydantic import BaseModel, Field
from dataclasses import dataclass, field

from .utility import Composition, convert_density_to_atoms_per_cubic_angstrom
from .pattern import Pattern
from .methods import FourierTransformMethod, NormalizationMethod, ExtrapolationMethod


@dataclass
class SampleConfig:
    composition: Composition = field(default_factory=dict)
    density: float | None = None
    atomic_density: float | None = None

    def __post_init__(self):
        if self.density is not None:
            self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(
                self.composition, self.density
            )


@dataclass
class FitNormalization:
    TYPE: Literal["fit"] = "fit"
    q_cutoff: float = 3.0
    method: str = "squared"
    multiple_scattering: bool = False
    incoherent_scattering: bool = True
    container_scattering: Optional[Composition] = None


@dataclass
class IntNormalization:
    TYPE: Literal["integral"] = "integral"
    attenuation_factor: float = 0.001
    incoherent_scattering: bool = True


@dataclass
class OptimizeConfig:
    r_cutoff: float = 1.4
    iterations: int = 5
    use_modification_fcn: bool = False


@dataclass
class ExtrapolationConfig:
    method: ExtrapolationMethod = ExtrapolationMethod.STEP
    overlap: float = 0.2
    replace: bool = False


@dataclass
class TransformConfig:
    q_min: float = 0.0
    q_max: float = 10.0

    r_min: float = 0.0
    r_max: float = 10.0
    r_step: float = 0.01

    normalization: FitNormalization | IntNormalization = field(
        default_factory=FitNormalization
    )

    extrapolation_config: ExtrapolationConfig = field(
        default_factory=ExtrapolationConfig
    )

    use_modification_fcn: bool = False
    kn_correction: bool = False
    wavelength: Optional[float] = None

    fourier_transform_method: FourierTransformMethod = FourierTransformMethod.FFT


@dataclass
class Config:
    sample: SampleConfig = field(default_factory=SampleConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    optimize: Optional[OptimizeConfig] = None


class Input(BaseModel):
    data: Pattern
    bkg: Pattern | None = None
    bkg_scaling: float = 1.0
    config: Config = Config()


class Result(BaseModel):
    input: Input
    sq: Pattern
    fr: Pattern
    gr: Pattern


def create_input(
    data: Pattern,
    composition: Composition,
    density: float,
    bkg: Pattern = None,
    bkg_scaling: float = 1,
) -> Input:
    """
    Helper function to create a starting glassure input configuration.
    Automatically sets the q_min and q_max values to the first and last
    x-value of the data pattern - thus, the whole pattern gets transformed,
    when using this configuration.

    :param data: The data pattern.
    :param composition: The composition of the sample.
    :param density: The density of the sample in g/cm^3.
    :param bkg: The background pattern. None if no background is present.
    :param bkg_scaling: The scaling factor for the background pattern.
    """
    sample_config = SampleConfig(composition=composition, density=density)
    input_config = Input(
        data=data,
        bkg=bkg,
        bkg_scaling=bkg_scaling,
        config=Config(sample=sample_config),
    )
    input_config.config.transform.q_min = data.x[0]
    input_config.config.transform.q_max = data.x[-1]
    return input_config

# -*- coding: utf-8 -*/:

from typing import Optional, Literal
from pydantic import BaseModel, Field
from dataclasses import dataclass, field

from .utility import Composition, convert_density_to_atoms_per_cubic_angstrom
from .pattern import Pattern
from .methods import FourierTransformMethod, NormalizationMethod, ExtrapolationMethod


class SampleConfig(BaseModel):
    composition: Composition = field(default_factory=dict)
    density: Optional[float] = field(
        default=None,
    )
    atomic_density: Optional[float] = field(
        default=None,
    )

    def model_post_init(self, __context):
        if self.density is not None:
            self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(
                self.composition, self.density
            )


class FitNormalization(BaseModel):
    TYPE: Literal["fit"] = Field(default="fit", description="Normalization type")
    q_cutoff: float = Field(
        default=3.0,
        description="Cutoff q in 1/A for the normalization. Only above this value the normalization is performed.",
    )
    method: str = Field(
        default="squared",
        description='How to scale the values in respect to q during fitting. "linear" or "squared" are possible.',
    )
    multiple_scattering: bool = Field(
        default=False,
        description="Whether to consider multiple scattering - if true, the multiple scattering is approximated by a constant value.",
    )
    incoherent_scattering: bool = Field(
        default=True,
        description="Whether to subtract the incoherent scattering during the normalization.",
    )
    container_scattering: Optional[Composition] = Field(
        default=None,
        description="""Composition of the container material in the experiment. Only the incoherent scattering of the
         container is considered. The container scattering is subtracted from the total scattering and the amount is 
         fitted by just muliplying it with a constant value.""",
    )


class IntNormalization(BaseModel):
    TYPE: Literal["integral"] = Field(
        default="integral", description="Normalization type"
    )
    attenuation_factor: float = Field(
        default=0.001, description="Attenuation factor for the normalization"
    )
    incoherent_scattering: bool = Field(
        default=True,
        description="Whether to subtract the incoherent scattering during the normalization",
    )


class OptimizeConfig(BaseModel):
    r_cutoff: float = Field(
        default=1.4,
        description="Cutoff r for the Kaplow optimization scheme. Should be below the first peak in g(r).",
    )
    iterations: int = Field(
        default=5, description="Number of iterations for the Kaplow optimization."
    )
    use_modification_fcn: bool = Field(
        default=False,
        description="Whether to use the Lorch modification function during the optimization procedure. "
        + "This can be different from the transform configuration.",
    )


class ExtrapolationConfig(BaseModel):
    method: ExtrapolationMethod = Field(
        default=ExtrapolationMethod.STEP,
        description="Method for the extrapolation of the structure factor S(q) from q_min to zero.",
    )
    s0: Optional[float] = Field(
        default=None,
        description="Target value at S(0) for the extrapolation to. If is None, the theorethical value is used.",
    )
    overlap: float = Field(
        default=0.2,
        description="Overlap in q-space [1/A] for the extrapolation. E.g. the fitting range.",
    )
    replace: bool = Field(
        default=False,
        description="Whether to replace the original S(q) data in the overlap region with the extrapolated values.",
    )


class TransformConfig(BaseModel):
    q_min: float = Field(
        default=0.0,
        description="Minimum q in 1/Angstrom from the data. Below it will be extended to zero.",
    )
    q_max: float = Field(
        default=10.0, description="Maximum q in 1/Angstrom from the data."
    )

    r_min: float = Field(
        default=0.0,
        description="Minimum r in Angstrom for the calculated  pair distribution function g(r).",
    )
    r_max: float = Field(
        default=10.0,
        description="Maximum r in Angstrom for the calculated pair distribution function g(r).",
    )
    r_step: float = Field(
        default=0.01,
        description="Step size for the r values in Angstrom for the calculated pair distribution function g(r).",
    )

    normalization: FitNormalization | IntNormalization = field(
        default_factory=FitNormalization
    )

    extrapolation: ExtrapolationConfig = field(default_factory=ExtrapolationConfig)

    use_modification_fcn: bool = False
    kn_correction: bool = False
    wavelength: Optional[float] = None

    fourier_transform_method: FourierTransformMethod = FourierTransformMethod.FFT


class Config(BaseModel):
    """Main configuration model for the glassure data processing. Does not contain any data, but only the information
    how to process the dataset."""

    sample: SampleConfig = Field(
        default_factory=SampleConfig,
        description="Sample configuration model, containing the composition and density of the material.",
    )
    transform: TransformConfig = Field(
        default_factory=TransformConfig,
        description="""Transform configuration model, containing the normalization, transform and 
        extrapolation settings.""",
    )
    optimize: Optional[OptimizeConfig] = Field(
        default=None,
        description="Optimization configuration model. If None, no optimization is performed",
    )


class Input(BaseModel):
    """Main input configuration for the glassure data processing. contains data and configuration."""

    data: Optional[Pattern] = None
    bkg: Optional[Pattern] = None
    bkg_scaling: float = 1.0
    config: Config = Config()


class Result(BaseModel):
    input: Input
    sq: Optional[Pattern] = None
    fr: Optional[Pattern] = None
    gr: Optional[Pattern] = None


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

    :return: The input configuration.
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

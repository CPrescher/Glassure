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

    normalization: FitNormalization | IntNormalization = Field(
        default_factory=FitNormalization,
        description="Normalization configuration model. Possible values are :class:`FitNormalization` or "
        + ":class:`IntNormalization`.",
    )

    extrapolation: ExtrapolationConfig = Field(
        default_factory=ExtrapolationConfig, description="Extrapolation configuration model."
    )

    use_modification_fcn: bool = Field(
        default=False, description="Whether to use the Lorch modification function."
    )
    kn_correction: bool = Field(
        default=False,
        description="Whether to apply the Klein-Nishima correction to the Compton scattering of the sample and the"
        + "container (defined in normalization).",
    )
    wavelength: Optional[float] = Field(default=None, description="Wavelength in Angstrom. Needs to be set for the "
                                                               + "Klein-Nishima correction.")   

    fourier_transform_method: FourierTransformMethod = FourierTransformMethod.FFT


class CalculationConfig(BaseModel):
    """Main  calculation configuration model for the glassure data processing.
    Does not contain any data, but only the information how to process the dataset.

    To reuse the calculation config for a different calculation with some parameters changed, it is advised to use the
    model_copy(deep=True) method of the config.

    This will create a deep copy of the configuration object and not
    overwrite parameters of the original one. (see https://docs.pydantic.dev/latest/concepts/serialization/#model_copy
    for more information).

    For example:
    ```
    config = CalculationConfig()
    config.sample.composition = {"Si": Si, "O": 2}

    config_copy = config.model_copy(deep=True)
    config_copy.sample.composition = {"Ge": 1, "O": 2}
    ```
    """

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


class DataConfig(BaseModel):
    """Configuration for the collected data, containing the data pattern, the background pattern and the bkg scaling
    parameter."""

    data: Pattern = Field(description="The data pattern.")
    bkg: Optional[Pattern] = Field(default=None, description="The background pattern.")
    bkg_scaling: float = Field(
        default=1.0, description="The scaling factor for the background pattern."
    )


class Result(BaseModel):
    calculation_config: CalculationConfig = Field(
        description="The configuration used for the calculation."
    )
    sq: Optional[Pattern] = Field(
        default=None, description="The calculated structure factor S(q)."
    )
    fr: Optional[Pattern] = Field(
        default=None, description="The calculated pair distribution function F(r)."
    )
    gr: Optional[Pattern] = Field(default=None, description="The calculated g(r).")

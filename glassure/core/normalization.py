import numpy as np

from dataclasses import dataclass
from .pattern import Pattern
from .methods import ScatteringFactorSource, NormalizationFitScaling


@dataclass
class SampleData:
    sample_pattern: Pattern
    density: float
    composition: dict


@dataclass
class NormalizationData:
    sf_source: ScatteringFactorSource


class IntegralNormalizationData(NormalizationData):
    attenuation_factor: float


class FaberZimanFitNormalizationData(NormalizationData):
    q_cutoff: float = 6
    scaling: NormalizationFitScaling = NormalizationFitScaling.QUADRATIC
    use_incoherent_scattering: bool = True
    use_extra_diamond: bool = False


@dataclass
class NormalizationResult:
    n_factor: float
    normalized_pattern: Pattern
    compton_background: np.ndarray


class FitNormalizationResult(NormalizationResult):
    extra_diamond: np.ndarray


def normalize_integral_faber_ziman(
    sample_data: SampleData, normalization_data: IntegralNormalizationData
) -> NormalizationResult:
    pass


def normalize_integral_ashcroft_langreth(
    sample_data: SampleData,
    normalization_data: IntegralNormalizationData
) -> NormalizationResult:
    pass


def normalize_fit_faber_ziman(
    sample_data: SampleData, normalization_data: FaberZimanFitNormalizationData
) -> FitNormalizationResult:
    pass


# we could combine sample_pattern, sf_source, and composition into a single object
# how should we name it?

from enum import Enum


class NormalizationMethod(Enum):
    """
    Enum class for the different methods to perform an intensity normalization.
    """

    INTEGRAL = "integral"
    FIT = "fit"


class FourierTransformMethod(Enum):
    """
    Enum class for the different methods to perform a Fourier transform.
    """

    FFT = "fft"
    INTEGRAL = "integral"


class ScatteringFactorSource(Enum):
    """
    Enum class for the different sources of the scattering factors.
    """

    HAJDU = "hajdu"
    BROWN_HUBBELL = "brown_hubbell"


class NormalizationFitScaling(Enum):
    """
    Enum class for the different scaling methods for the fit.
    """

    LINEAR = "linear"
    QUADRATIC = "quadratic"

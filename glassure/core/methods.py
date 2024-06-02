from enum import Enum


class NormalizationMethod(str, Enum):
    """
    Enum class for the different methods to perform an intensity normalization.
    """

    INTEGRAL = "integral"
    FIT = "fit"


class FourierTransformMethod(str, Enum):
    """
    Enum class for the different methods to perform a Fourier transform.
    """

    FFT = "fft"
    INTEGRAL = "integral"


class ScatteringFactorSource(str, Enum):
    """
    Enum class for the different sources of the scattering factors.
    """

    HAJDU = "hajdu"
    BROWN_HUBBELL = "brown_hubbell"


class NormalizationFitScaling(str, Enum):
    """
    Enum class for the different scaling methods for the fit.
    """

    LINEAR = "linear"
    QUADRATIC = "quadratic"


class ExtrapolationMethod(str, Enum):
    """
    Enum class for the different extrapolation methods of the S(Q) to
    S(0)
    """

    STEP = "step"
    LINEAR = "linear"
    POLY = "poly"
    SPLINE = "spline"


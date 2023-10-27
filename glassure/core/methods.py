from enum import Enum


class SqMethod(Enum):
    """
    Enum class for the different methods to calculate the structure factor.
    """
    FZ = 'FZ'
    AL = 'AL'


class NormalizationMethod(Enum):
    """
    Enum class for the different methods to perform an intensity normalization.
    """
    INTEGRAL = 'integral'
    FIT = 'fit'


class FourierTransformMethod(Enum):
    """
    Enum class for the different methods to perform a Fourier transform.
    """
    FFT = 'fft'
    INTEGRAL = 'integral'

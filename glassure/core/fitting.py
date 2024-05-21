# -*- coding: utf-8 -*-

import numpy as np

from .utility import calculate_weighting_factor
from .transform import calculate_fr
from .pattern import Pattern


def i_q_peak(q, n, position, sigma, composition, element_1, element_2):
    """
    Calculates the contribution of one element 1 - element 2 peak in real space to i(Q) (remember i(Q)=S(Q)-1). We
    assume a gaussian broadening. The math is explained in the paper about NXFit (Pickup et al. 2014, J. Appl. Cryst.
    47, 1790-1796).

    :param q: Q value or numpy array with a unit of A^-1
    :param n: coordination number of element 2 to element 1
    :param position: average distance between the two elements
    :param sigma: measure for broadness of distances distribution
    :param composition: composition: dictionary with elements as key and abundances as relative numbers
    :param element_1: string giving element 1
    :param element_2: string giving element 1
    """
    num_atoms = sum([val for _, val in composition.items()])
    c_2 = composition[element_2] / num_atoms
    w = calculate_weighting_factor(composition, element_1, element_2, q)
    return n * w / c_2 * np.sin(q * position) / (q * position) * np.exp(-q ** 2 * sigma ** 2 / 2)


def t_r_peak(r, n, position, sigma, composition, element_1, element_2, q, use_modification_fcn=False, method='fft'):
    """
    Calculates the contribution of one element 1 - element 2 peak in real space to t(r). We assume a gaussian
    broadening. The math is explained in the paper about NXFit (Pickup et al. 2014, J. Appl. Cryst. 47, 1790-1796).

    The function will first calculate the peak in i(Q) with the appropriate weighting factor and then fourier transform
    it into real space.

    :param r: numpy array giving the r-values for which the peak will be calculated
    :param n: coordination number of element 2 to element 1
    :param position: average distance between the two elements
    :param sigma: measure for broadness of distances distribution
    :param composition: composition: dictionary with elements as key and abundances as relative numbers
    :param element_1: string giving element 1
    :param element_2: string giving element 1
    :param q: numpy array giving the q-values for which the peak will be calculated in q-space, should correspond to
                  the same values as the experimental data.
                  WARNING: check whether it works correctly, when your q values are not extended to close 0 A^{-1}.
                  WARNING: q-array should not contain 0, since this will cause a division by zero and the calculation
                  will fail.
    :param use_modification_fcn: boolean flag whether to use the Lorch modification function, during the fourier
                                 transformation.
    :param method: determines the method used for calculating fr, possible values are:
                    - 'integral' solves the Fourier integral, by calculating the integral
                    - 'fft' solves the Fourier integral by using fast fourier transformation
    """
    q_peak = i_q_peak(q, n, position, sigma, composition, element_1, element_2)
    return calculate_fr(Pattern(q, q_peak + 1), r, use_modification_fcn=use_modification_fcn, method=method).y

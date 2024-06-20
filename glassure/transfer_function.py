# -*- coding: utf-8 -*-

import numpy as np
from scipy.interpolate import UnivariateSpline
from .pattern import Pattern


def calculate_transfer_function(std_pattern: Pattern, sample_pattern: Pattern, smooth_factor=1) -> UnivariateSpline:
    """

    :param std_pattern: the Diffraction pattern how it should look like, should be already background subtracted
    :type std_pattern: Pattern
    :param sample_pattern: the Diffraction pattern of the same sample which needs a transfer function
    :param smooth_factor: Determines the amount of smoothing of the transfer function
    :return:
    """
    transfer_function = std_pattern.y / sample_pattern.y
    transfer_function /= np.min(transfer_function)

    return UnivariateSpline(std_pattern.x, transfer_function, k=3, s=smooth_factor)

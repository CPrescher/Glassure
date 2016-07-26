# -*- coding: utf8 -*-

from scipy.interpolate import UnivariateSpline
from .pattern import Pattern

def calculate_transfer_function(std_pattern, sample_pattern):
    """

    :param std_pattern: the Diffraction pattern how it should look like, should be already background subtracted
    :type std_pattern: Pattern
    :param sample_pattern: the Diffraction pattern of the same sample which needs a transfer function
    :return:
    """
    transfer_function = std_pattern.y/sample_pattern.y
    return UnivariateSpline(std_pattern.x, transfer_function, k=3, s=len(transfer_function)/1.8)
# -*- coding: utf8 -*-
from colorsys import hsv_to_rgb
from copy import deepcopy

import numpy as np

from core.pattern import Pattern


class GlassureConfiguration(object):
    num = 0

    def __init__(self):
        super(GlassureConfiguration, self).__init__()
        # initialize all spectra
        self.original_pattern = Pattern()
        self.background_pattern = Pattern()

        self.diamond_bkg_pattern = None

        self.sq_pattern = None
        self.fr_pattern = None
        self.gr_pattern = None

        # initialize all parameters
        self.composition = {}

        self.density = 2.2
        self.density_error = None

        self.q_min = 0.0
        self.q_max = 10.0

        self.r_min = 0.5
        self.r_max = 10
        self.r_step = 0.01

        # optimization parameters
        self.optimize = False
        self.optimize_r_cutoff = 1.4
        self.optimize_iterations = 5
        self.optimize_attenuation = 1

        # initialize all Flags
        self.use_modification_fcn = False

        self.extrapolation_method = 'step'
        self.extrapolation_parameters = {'q_max': 2, 'replace':False}

        self.name = 'Config {}'.format(GlassureConfiguration.num)
        self.color = calculate_color(GlassureConfiguration.num)
        GlassureConfiguration.num += 1

    def copy(self):
        new_configuration = deepcopy(self)
        new_configuration.name = 'Config {}'.format(GlassureConfiguration.num)
        new_configuration.color = calculate_color(GlassureConfiguration.num)
        GlassureConfiguration.num += 1

        return new_configuration


def calculate_color(ind):
    s = 0.8
    v = 0.8
    h = (0.19 * (ind + 2)) % 1
    return np.array(hsv_to_rgb(h, s, v)) * 255

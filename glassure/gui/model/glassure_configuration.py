# -*- coding: utf8 -*-

from core.pattern import Pattern


class GlassureConfiguration(object):
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

        self.r_cutoff = 1.4

        # initialize all Flags
        self.use_modification_fcn = False

        self.extrapolation_method = None
        self.extrapolation_parameters = None

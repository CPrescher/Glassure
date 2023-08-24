# -*- coding: utf-8 -*/:
from __future__ import annotations
from colorsys import hsv_to_rgb
from copy import deepcopy

import numpy as np

from ...core.pattern import Pattern


class GlassureConfiguration(object):
    num = 0

    def __init__(self):
        super(GlassureConfiguration, self).__init__()
        # initialize all spectra
        self.original_pattern = Pattern()
        self.background_pattern = None

        self.diamond_bkg_pattern = None

        self.sq_pattern = None
        self.fr_pattern = None
        self.gr_pattern = None

        # initialize all parameters
        self.sf_source = 'hajdu'
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
        self.extrapolation_parameters = {'q_max': 2, 'replace': False}

        # soller slit correction parameters
        self.use_soller_correction = False
        self.soller_correction = None
        # default parameters for soller slit ID27, ESRF and GSECARS, APS
        self.soller_parameters = {'sample_thickness': 1.0,  # in mm
                                  'wavelength': 0.31,  # in Angstrom
                                  'inner_radius': 62,  # in mm
                                  'outer_radius': 210,  # in mm
                                  'inner_width': 0.05,  # in mm
                                  'outer_width': 0.2,  # in mm
                                  'inner_length': 8,  # in mm
                                  'outer_length': 6}  # in mm

        # transfer function stuff
        self.use_transfer_function = False
        self.transfer_function = None
        self.transfer_function_smoothing = 1.0
        self.transfer_std_pattern = None
        self.transfer_std_bkg_pattern = None
        self.transfer_std_bkg_scaling = 1.0
        self.transfer_sample_pattern = None
        self.transfer_sample_bkg_pattern = None
        self.transfer_sample_bkg_scaling = 1

        self.name = 'Config {}'.format(GlassureConfiguration.num)
        self.color = calculate_color(GlassureConfiguration.num)
        GlassureConfiguration.num += 1

    def copy(self):
        new_configuration = deepcopy(self)
        new_configuration.name = 'Config {}'.format(GlassureConfiguration.num)
        new_configuration.color = calculate_color(GlassureConfiguration.num)
        GlassureConfiguration.num += 1

        return new_configuration

    def to_dict(self) -> dict:
        config_dict = {
            'original_pattern': self.original_pattern.to_dict(),
            'background_pattern': self.background_pattern.to_dict() if self.background_pattern is not None else None,
            'diamond_bkg_pattern': self.diamond_bkg_pattern.to_dict() if self.diamond_bkg_pattern is not None else None,
            'sq_pattern': self.sq_pattern.to_dict()
            if self.sq_pattern is not None else None,
            'fr_pattern': self.fr_pattern.to_dict() if self.fr_pattern is not None else None,
            'gr_pattern': self.gr_pattern.to_dict() if self.gr_pattern is not None else None,
            'sf_source': self.sf_source,
            'composition': self.composition,
            'density': self.density,
            'density_error': self.density_error,
            'q_min': self.q_min,
            'q_max': self.q_max,
            'r_min': self.r_min,
            'r_max': self.r_max,
            'r_step': self.r_step,
            'optimize': self.optimize,
            'optimize_r_cutoff': self.optimize_r_cutoff,
            'optimize_iterations': self.optimize_iterations,
            'optimize_attenuation': self.optimize_attenuation,
            'use_modification_fcn': self.use_modification_fcn,
            'extrapolation_method': self.extrapolation_method,
            'extrapolation_parameters': self.extrapolation_parameters,
            'use_soller_correction': self.use_soller_correction,
            'soller_correction': self.soller_correction,
            'soller_parameters': self.soller_parameters,
            'use_transfer_function': self.use_transfer_function,
            'transfer_function': self.transfer_function,
            'transfer_function_smoothing': self.transfer_function_smoothing,
            'transfer_std_pattern': self.transfer_std_pattern.to_dict() if self.transfer_std_pattern is not None else None,
            'transfer_std_bkg_pattern': self.transfer_std_bkg_pattern.to_dict() if self.transfer_std_bkg_pattern is not None else None,
            'transfer_std_bkg_scaling': self.transfer_std_bkg_scaling,
            'transfer_sample_pattern': self.transfer_sample_pattern.to_dict() if self.transfer_sample_pattern is not None else None,
            'transfer_sample_bkg_pattern': self.transfer_sample_bkg_pattern.to_dict() if self.transfer_sample_bkg_pattern is not None else None,
            'transfer_sample_bkg_scaling': self.transfer_sample_bkg_scaling,
            'name': self.name,
            'color': self.color.tolist()
        }
        return config_dict

    @classmethod
    def from_dict(cls, config_dict: dict) -> GlassureConfiguration:
        config = cls()
        config.original_pattern = Pattern.from_dict(
            config_dict['original_pattern'])
        config.background_pattern = Pattern.from_dict(
            config_dict['background_pattern']) if config_dict['background_pattern'] is not None else None
        config.diamond_bkg_pattern = Pattern.from_dict(
            config_dict['diamond_bkg_pattern']) if config_dict['diamond_bkg_pattern'] is not None else None
        config.sq_pattern = Pattern.from_dict(
            config_dict['sq_pattern']) if config_dict['sq_pattern'] is not None else None
        config.fr_pattern = Pattern.from_dict(
            config_dict['fr_pattern']) if config_dict['fr_pattern'] is not None else None
        config.gr_pattern = Pattern.from_dict(
            config_dict['gr_pattern']) if config_dict['gr_pattern'] is not None else None
        config.sf_source = config_dict['sf_source']
        config.composition = config_dict['composition']
        config.density = config_dict['density']
        config.density_error = config_dict['density_error']
        config.q_min = config_dict['q_min']
        config.q_max = config_dict['q_max']
        config.r_min = config_dict['r_min']
        config.r_max = config_dict['r_max']
        config.r_step = config_dict['r_step']
        config.optimize = config_dict['optimize']
        config.optimize_r_cutoff = config_dict['optimize_r_cutoff']
        config.optimize_iterations = config_dict['optimize_iterations']
        config.optimize_attenuation = config_dict['optimize_attenuation']
        config.use_modification_fcn = config_dict['use_modification_fcn']
        config.extrapolation_method = config_dict['extrapolation_method']
        config.extrapolation_parameters = config_dict['extrapolation_parameters']
        config.use_soller_correction = config_dict['use_soller_correction']
        config.soller_correction = np.array(config_dict['soller_correction'])
        config.soller_parameters = config_dict['soller_parameters']
        config.use_transfer_function = config_dict['use_transfer_function']
        config.transfer_function = np.array(config_dict['transfer_function'])
        config.transfer_function_smoothing = config_dict['transfer_function_smoothing']
        config.transfer_std_pattern = Pattern.from_dict(
            config_dict['transfer_std_pattern']) if config_dict['transfer_std_pattern'] is not None else None
        config.transfer_std_bkg_pattern = Pattern.from_dict(
            config_dict['transfer_std_bkg_pattern']) if config_dict['transfer_std_bkg_pattern'] is not None else None
        config.transfer_std_bkg_scaling = config_dict['transfer_std_bkg_scaling']
        config.transfer_sample_pattern = Pattern.from_dict(
            config_dict['transfer_sample_pattern']) if config_dict['transfer_sample_pattern'] is not None else None
        config.transfer_sample_bkg_pattern = Pattern.from_dict(
            config_dict['transfer_sample_bkg_pattern']) if config_dict['transfer_sample_bkg_pattern'] is not None else None
        config.transfer_sample_bkg_scaling = config_dict['transfer_sample_bkg_scaling']
        config.name = config_dict['name']
        config.color = np.array(config_dict['color'])

        return config


def calculate_color(ind):
    s = 0.8
    v = 0.8
    h = (0.19 * (ind + 2)) % 1
    return np.array(hsv_to_rgb(h, s, v)) * 255

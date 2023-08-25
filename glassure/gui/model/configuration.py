# -*- coding: utf-8 -*/:
from __future__ import annotations
from colorsys import hsv_to_rgb
from copy import deepcopy

import numpy as np

from ...core.pattern import Pattern


class TransformConfiguration(object):
    def __init__(self):
        self.sf_source = 'hajdu'
        self.use_modification_fcn = False

        self.q_min = 0.0
        self.q_max = 10.0

        self.r_min = 0.5
        self.r_max = 10
        self.r_step = 0.01

    def to_dict(self):
        return {'sf_source': self.sf_source,
                'use_modification_fcn': self.use_modification_fcn,
                'q_min': self.q_min,
                'q_max': self.q_max,
                'r_min': self.r_min,
                'r_max': self.r_max,
                'r_step': self.r_step}

    @classmethod
    def from_dict(cls, transform_config: dict):
        config = cls()
        config.sf_source = transform_config['sf_source']
        config.use_modification_fcn = transform_config['use_modification_fcn']
        config.q_min = transform_config['q_min']
        config.q_max = transform_config['q_max']
        config.r_min = transform_config['r_min']
        config.r_max = transform_config['r_max']
        config.r_step = transform_config['r_step']

        return config


class OptimizeConfiguration(object):
    def __init__(self):
        self.enable = False
        self.r_cutoff = 1.4
        self.iterations = 5
        self.attenuation = 1

    def to_dict(self):
        return {'enable': self.enable,
                'r_cutoff': self.r_cutoff,
                'iterations': self.iterations,
                'attenuation': self.attenuation}

    @classmethod
    def from_dict(cls, optimize_config: dict):
        config = cls()
        config.enable = optimize_config['enable']
        config.r_cutoff = optimize_config['r_cutoff']
        config.iterations = optimize_config['iterations']
        config.attenuation = optimize_config['attenuation']

        return config


class ExtrapolationConfiguration(object):
    def __init__(self):
        self.method = 'step'
        self.parameters = {'q_max': 2, 'replace': False}

    def to_dict(self):
        return {'method': self.method,
                'parameters': self.parameters}

    @classmethod
    def from_dict(cls, extrapolation_config: dict):
        config = cls()
        config.method = extrapolation_config['method']
        config.parameters = extrapolation_config['parameters']

        return config


class Sample(object):
    def __init__(self):
        self.composition = {}
        self.density = 2.2
        self.density_error = None

    def to_dict(self):
        return {'composition': self.composition,
                'density': self.density,
                'density_error': self.density_error}

    @classmethod
    def from_dict(cls, sample_config: dict):
        config = cls()
        config.composition = sample_config['composition']
        config.density = sample_config['density']
        config.density_error = sample_config['density_error']

        return config


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
        self.sample = Sample()
        self.transform_config = TransformConfiguration()
        self.optimize_config = OptimizeConfiguration()
        self.extrapolation_config = ExtrapolationConfiguration()

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
            'sample': self.sample.to_dict(),
            'transform_configuration': self.transform_config.to_dict(),
            'optimize_configuration': self.optimize_config.to_dict(),
            'extrapolation_configuration': self.extrapolation_config.to_dict(),
            'use_soller_correction': self.use_soller_correction,
            'soller_correction': self.soller_correction.tolist() if self.soller_correction is not None else None,
            'soller_parameters': self.soller_parameters,
            'use_transfer_function': self.use_transfer_function,
            'transfer_function': self.transfer_function.tolist() if self.transfer_function is not None else None,
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
        config.sample = Sample.from_dict(config_dict['sample'])
        config.transform_config = TransformConfiguration.from_dict(
            config_dict['transform_configuration'])
        config.optimize_config = OptimizeConfiguration.from_dict(
            config_dict['optimize_configuration'])
        config.extrapolation_config = ExtrapolationConfiguration.from_dict(
            config_dict['extrapolation_configuration'])

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

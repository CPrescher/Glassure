# -*- coding: utf-8 -*/:
from __future__ import annotations
from colorsys import hsv_to_rgb
from copy import deepcopy

import numpy as np

from ...core.pattern import Pattern
from ...core.methods import SqMethod, NormalizationMethod, FourierTransformMethod


class TransformConfiguration(object):
    def __init__(self):
        self.use_modification_fcn: bool = False
        self.sq_method: SqMethod = SqMethod.FZ
        self.normalization_method = NormalizationMethod.INTEGRAL
        self.fourier_transform_method = FourierTransformMethod.FFT

        self.q_min: float = 0.0
        self.q_max: float = 10.0

        self.r_min: float = 0.5
        self.r_max: float = 10
        self.r_step: float = 0.01

    def to_dict(self):
        return {
            "use_modification_fcn": self.use_modification_fcn,
            "sq_method": self.sq_method.value,
            "normalization_method": self.normalization_method.value,
            "fourier_transform_method": self.fourier_transform_method.value,
            "q_min": self.q_min,
            "q_max": self.q_max,
            "r_min": self.r_min,
            "r_max": self.r_max,
            "r_step": self.r_step,
        }

    @classmethod
    def from_dict(cls, transform_config: dict) -> TransformConfiguration:
        config = cls()
        for key in transform_config.keys():
            if not hasattr(config, key):
                continue
            if key == "sq_method":
                setattr(config, key, SqMethod(transform_config[key]))
            elif key == "normalization_method":
                setattr(config, key, NormalizationMethod(transform_config[key]))
            elif key == "fourier_transform_method":
                setattr(config, key, FourierTransformMethod(transform_config[key]))
            else:
                setattr(config, key, transform_config[key])
        return config


class OptimizeConfiguration(object):
    def __init__(self):
        self.enable = False
        self.r_cutoff = 1.4
        self.iterations = 5
        self.attenuation = 1

    def to_dict(self):
        return vars(self)

    @classmethod
    def from_dict(cls, optimize_config: dict):
        config = cls()
        for key in optimize_config.keys():
            if not hasattr(config, key):
                continue
            setattr(config, key, optimize_config[key])
        return config


class ExtrapolationConfiguration(object):
    def __init__(self):
        self.activate: bool = False
        self.method = "step"
        self.fit_q_max: float = 2.0
        self.fit_replace: bool = False
        self.s0: float = 0.0
        self.s0_auto: bool = True

    def to_dict(self):
        return vars(self)

    @classmethod
    def from_dict(cls, extrapolation_config: dict):
        config = cls()
        for key in extrapolation_config.keys():
            if not hasattr(config, key):
                continue
            setattr(config, key, extrapolation_config[key])
        return config


class Sample:
    def __init__(self):
        self.sf_source = "hajdu"
        self.composition = {}
        self.density = 2.2
        self.density_error = None

    def to_dict(self):
        return vars(self)

    @classmethod
    def from_dict(cls, sample_config: dict):
        config = cls()
        for key in sample_config.keys():
            if not hasattr(config, key):
                continue
            setattr(config, key, sample_config[key])
        return config


class SollerConfiguration(object):
    def __init__(self):
        self.enable = False
        self.correction = None
        self.parameters = {
            "sample_thickness": 1.0,  # in mm
            "wavelength": 0.31,  # in Angstrom
            "inner_radius": 62,  # in mm
            "outer_radius": 210,  # in mm
            "inner_width": 0.05,  # in mm
            "outer_width": 0.2,  # in mm
            "inner_length": 8,  # in mm
            "outer_length": 6,
        }  # in mm

    def to_dict(self):
        return {
            "enable": self.enable,
            "correction": (
                self.correction.tolist() if self.correction is not None else None
            ),
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, soller_config: dict):
        config = cls()
        config.enable = soller_config["enable"]
        config.correction = (
            np.array(soller_config["correction"])
            if soller_config["correction"] is not None
            else None
        )
        config.parameters = soller_config["parameters"]

        return config


class TransferConfiguration(object):
    def __init__(self):
        self.enable = False
        self.function = None
        self.smoothing = 1.0
        self.std_pattern = None
        self.std_bkg_pattern = None
        self.std_bkg_scaling = 1.0
        self.sample_pattern = None
        self.sample_bkg_pattern = None
        self.sample_bkg_scaling = 1.0

    def to_dict(self):
        return {
            "enable": self.enable,
            "smoothing": self.smoothing,
            "std_pattern": (
                self.std_pattern.to_dict() if self.std_pattern is not None else None
            ),
            "std_bkg_pattern": (
                self.std_bkg_pattern.to_dict()
                if self.std_bkg_pattern is not None
                else None
            ),
            "std_bkg_scaling": self.std_bkg_scaling,
            "sample_pattern": (
                self.sample_pattern.to_dict()
                if self.sample_pattern is not None
                else None
            ),
            "sample_bkg_pattern": (
                self.sample_bkg_pattern.to_dict()
                if self.sample_bkg_pattern is not None
                else None
            ),
            "sample_bkg_scaling": self.sample_bkg_scaling,
        }

    @classmethod
    def from_dict(cls, transfer_config: dict):
        config = cls()
        config.enable = transfer_config["enable"]
        config.smoothing = transfer_config["smoothing"]
        config.std_pattern = (
            Pattern.from_dict(transfer_config["std_pattern"])
            if transfer_config["std_pattern"] is not None
            else None
        )
        config.std_bkg_pattern = (
            Pattern.from_dict(transfer_config["std_bkg_pattern"])
            if transfer_config["std_bkg_pattern"] is not None
            else None
        )
        config.std_bkg_scaling = transfer_config["std_bkg_scaling"]
        config.sample_pattern = (
            Pattern.from_dict(transfer_config["sample_pattern"])
            if transfer_config["sample_pattern"] is not None
            else None
        )
        config.sample_bkg_pattern = (
            Pattern.from_dict(transfer_config["sample_bkg_pattern"])
            if transfer_config["sample_bkg_pattern"] is not None
            else None
        )
        config.sample_bkg_scaling = transfer_config["sample_bkg_scaling"]

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
        self.soller_config = SollerConfiguration()
        self.transfer_config = TransferConfiguration()

        self.name = "Config {}".format(GlassureConfiguration.num)
        self.color = calculate_color(GlassureConfiguration.num)
        self.show = True
        GlassureConfiguration.num += 1

    def copy(self):
        new_configuration = deepcopy(self)
        new_configuration.name = "Config {}".format(GlassureConfiguration.num)
        new_configuration.color = calculate_color(GlassureConfiguration.num)
        GlassureConfiguration.num += 1

        return new_configuration

    def to_dict(self) -> dict:
        config_dict = {
            "original_pattern": self.original_pattern.to_dict(),
            "background_pattern": (
                self.background_pattern.to_dict()
                if self.background_pattern is not None
                else None
            ),
            "diamond_bkg_pattern": (
                self.diamond_bkg_pattern.to_dict()
                if self.diamond_bkg_pattern is not None
                else None
            ),
            "sq_pattern": (
                self.sq_pattern.to_dict() if self.sq_pattern is not None else None
            ),
            "fr_pattern": (
                self.fr_pattern.to_dict() if self.fr_pattern is not None else None
            ),
            "gr_pattern": (
                self.gr_pattern.to_dict() if self.gr_pattern is not None else None
            ),
            "sample": self.sample.to_dict(),
            "transform_configuration": self.transform_config.to_dict(),
            "optimize_configuration": self.optimize_config.to_dict(),
            "extrapolation_configuration": self.extrapolation_config.to_dict(),
            "soller_configuration": self.soller_config.to_dict(),
            "transfer_configuration": self.transfer_config.to_dict(),
            "name": self.name,
            "color": self.color.tolist(),
            "show": self.show,
        }
        return config_dict

    @classmethod
    def from_dict(cls, config_dict: dict) -> GlassureConfiguration:
        config = cls()

        def get_pattern_or_none(pattern_dict):
            if pattern_dict is None:
                return None
            else:
                return Pattern.from_dict(pattern_dict)

        config.original_pattern = get_pattern_or_none(config_dict["original_pattern"])
        config.background_pattern = get_pattern_or_none(
            config_dict["background_pattern"]
        )
        config.diamond_bkg_pattern = get_pattern_or_none(
            config_dict["diamond_bkg_pattern"]
        )
        config.sq_pattern = get_pattern_or_none(config_dict["sq_pattern"])
        config.fr_pattern = get_pattern_or_none(config_dict["fr_pattern"])
        config.gr_pattern = get_pattern_or_none(config_dict["gr_pattern"])

        config.sample = Sample.from_dict(config_dict["sample"])
        config.transform_config = TransformConfiguration.from_dict(
            config_dict["transform_configuration"]
        )
        config.optimize_config = OptimizeConfiguration.from_dict(
            config_dict["optimize_configuration"]
        )
        config.extrapolation_config = ExtrapolationConfiguration.from_dict(
            config_dict["extrapolation_configuration"]
        )
        config.soller_config = SollerConfiguration.from_dict(
            config_dict["soller_configuration"]
        )
        config.transfer_config = TransferConfiguration.from_dict(
            config_dict["transfer_configuration"]
        )

        config.name = config_dict["name"]
        config.color = np.array(config_dict["color"])
        config.show = config_dict["show"] if "show" in config_dict.keys() else True

        return config


def calculate_color(ind):
    s = 0.8
    v = 0.8
    h = (0.19 * (ind + 2)) % 1
    return np.array(hsv_to_rgb(h, s, v)) * 255

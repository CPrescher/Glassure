# -*- coding: utf-8 -*-
from pytest import approx

import numpy as np

from glassure.pattern import Pattern
from glassure.configuration import SampleConfig, FitNormalization, CalculationConfig


def test_sample_config():
    c = SampleConfig()
    c_dict = vars(c)
    assert c_dict == {"composition": {}, "density": None, "atomic_density": None}

    c = SampleConfig(composition={"Si": 1, "O": 2}, density=2.2)

    assert c.atomic_density == approx(0.0662, abs=1e-4)

    c_dict = vars(c)
    assert c_dict == {
        "composition": {"Si": 1, "O": 2},
        "density": 2.2,
        "atomic_density": approx(0.0662, abs=1e-4),
    }

    c = SampleConfig(composition={"Si": 1, "O": 2}, atomic_density=0.0662)
    assert c.density == None


def test_fit_normalization_config():
    c = FitNormalization()
    c_dict = vars(c)
    assert c_dict == {
        "TYPE": "fit",
        "q_cutoff": 3.0,
        "method": "squared",
        "multiple_scattering": False,
        "incoherent_scattering": True,
        "container_scattering": None,
    }

    c = FitNormalization(
        q_cutoff=2.0,
        method="linear",
        multiple_scattering=True,
        incoherent_scattering=False,
        container_scattering={"Si": 1, "O": 2},
    )

    c_dict = vars(c)
    assert c_dict == {
        "TYPE": "fit",
        "q_cutoff": 2.0,
        "method": "linear",
        "multiple_scattering": True,
        "incoherent_scattering": False,
        "container_scattering": {"Si": 1, "O": 2},
    }


def test_calculation_config():
    c = CalculationConfig()
    c_json = c.model_dump_json()
    assert type(c.model_dump()) == dict
    assert type(c_json) == str

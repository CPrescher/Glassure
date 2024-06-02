# -*- coding: utf-8 -*-
from pytest import approx
import json
from dataclasses import asdict

import numpy as np

from glassure.core.pattern import Pattern
from glassure.core.configuration import (
    SampleConfig,
    FitNormalization,
    Config,
    Input,
    create_input,
)


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
    c = Config()
    c_dict = asdict(c)
    test = json.dumps(c_dict)


def test_input_config():
    pattern = Pattern()

    input_config = Input(data=pattern)
    input_config_dict = input_config.model_dump()
    output = Input(**input_config_dict)

    assert np.array_equal(output.data.x, pattern.x)
    assert np.array_equal(output.data.y, pattern.y)


def test_create_input_config():
    x = np.arange(1, 13, 0.1)
    pattern = Pattern(x, np.sin(x))
    composition = {"Si": 1, "O": 2}
    density = 2.2

    input_config = create_input(pattern, composition, density)
    transform = input_config.config.transform

    # check that q limits are set correctly
    assert transform.q_min == approx(1.0)
    assert transform.q_max == np.max(x)

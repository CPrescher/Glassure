import os
import numpy as np

import matplotlib.pyplot as plt

from glassure.pattern import Pattern
from glassure.calc import process_input
from glassure.configuration import create_input, OptimizeConfig, IntNormalization


from . import unittest_data_path

data_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
bkg_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


def prepare_input():
    data_pattern = Pattern.from_file(data_path)
    bkg_pattern = Pattern.from_file(bkg_path)

    config = create_input(
        data_pattern,
        composition={"Mg": 2, "Si": 1, "O": 4},
        density=2.9,
        bkg=bkg_pattern,
    )
    config.config.transform.q_max = 20
    return config


def test_process_input_base():
    input = prepare_input()

    res = process_input(input)

    assert len(res.sq.x) > 0
    assert len(res.fr.x) > 0
    assert len(res.gr.x) > 0


def test_process_input_optimize_sq():
    input = prepare_input()
    res = process_input(input)

    input.config.optimize = OptimizeConfig()
    res_optimize = process_input(input)

    assert not np.array_equal(res.sq.y, res_optimize.sq.y)


def test_process_input_norm_int():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.normalization = IntNormalization()
    res_int = process_input(input)

    assert not np.array_equal(res.sq.y, res_int.sq.y)


def test_process_input_modification_fcn():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.use_modification_fcn = True
    res_mod = process_input(input)

    assert not np.array_equal(res.fr.y, res_mod.fr.y)


def test_process_input_linear_extrapolation():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.extrapolation.method = "linear"
    res_lin = process_input(input)

    assert not np.array_equal(res.sq.y, res_lin.sq.y)


def test_process_input_spline_extrapolation():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.extrapolation.method = "spline"
    res_spline = process_input(input)

    assert not np.array_equal(res.sq.y, res_spline.sq.y)


def test_process_input_poly_extrapolation():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.extrapolation.method = "poly"
    res_poly = process_input(input)

    assert not np.array_equal(res.sq.y, res_poly.sq.y)


def test_process_input_kn_correction():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.kn_correction = True
    input.config.transform.wavelength = 0.22

    res_kn = process_input(input)

    assert not np.array_equal(res.sq.y, res_kn.sq.y)


def test_process_input_with_container_scattering():
    input = prepare_input()
    res = process_input(input)

    input.config.transform.normalization.container_scattering = {"C": 1}

    res_container = process_input(input)

    assert not np.array_equal(res.sq.y, res_container.sq.y)


def test_process_input_with_container_scattering_and_kn():
    input = prepare_input()
    input.config.transform.kn_correction = True
    input.config.transform.wavelength = 0.22

    res = process_input(input)

    input.config.transform.normalization.container_scattering = {"C": 1}

    res_container = process_input(input)

    assert not np.array_equal(res.sq.y, res_container.sq.y)

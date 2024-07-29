import os
import numpy as np

from glassure.pattern import Pattern
from glassure.calc import calculate, create_process_configs
from glassure.configuration import OptimizeConfig, IntNormalization


from . import unittest_data_path

data_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
bkg_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


def prepare_input():
    data_pattern = Pattern.from_file(data_path)
    bkg_pattern = Pattern.from_file(bkg_path)

    data_config, calculation_config = create_process_configs(
        data_pattern,
        composition={"Mg": 2, "Si": 1, "O": 4},
        density=2.9,
        bkg=bkg_pattern,
    )
    calculation_config.transform.q_max = 20
    return data_config, calculation_config


def test_process_input_base():
    input = prepare_input()

    res = calculate(*input)

    assert len(res.sq.x) > 0
    assert len(res.fr.x) > 0
    assert len(res.gr.x) > 0


def test_process_input_optimize_sq():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.optimize = OptimizeConfig()
    res_optimize = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_optimize.sq.y)


def test_process_input_norm_int():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.normalization = IntNormalization()
    res_int = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_int.sq.y)


def test_process_input_modification_fcn():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.use_modification_fcn = True
    res_mod = calculate(data_input, calculation_input)

    assert not np.array_equal(res.fr.y, res_mod.fr.y)


def test_process_input_linear_extrapolation():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.extrapolation.method = "linear"
    res_lin = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_lin.sq.y)


def test_process_input_spline_extrapolation():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.extrapolation.method = "spline"
    res_spline = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_spline.sq.y)


def test_process_input_poly_extrapolation():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.extrapolation.method = "poly"
    res_poly = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_poly.sq.y)


def test_process_extrapolation_with_s0():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.extrapolation.method = "linear"
    calculation_input.transform.extrapolation.s0 = 0.1
    res_s0 = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_s0.sq.y)


def test_process_input_kn_correction():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.kn_correction = True
    calculation_input.transform.wavelength = 0.22

    res_kn = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_kn.sq.y)


def test_process_input_with_container_scattering():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)

    calculation_input.transform.normalization.container_scattering = {"C": 1}

    res_container = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_container.sq.y)


def test_process_input_with_container_scattering_and_kn():
    data_input, calculation_input = prepare_input()
    res = calculate(data_input, calculation_input)
    calculation_input.transform.kn_correction = True
    calculation_input.transform.wavelength = 0.22

    res = calculate(data_input, calculation_input)

    calculation_input.transform.normalization.container_scattering = {"C": 1}

    res_container = calculate(data_input, calculation_input)

    assert not np.array_equal(res.sq.y, res_container.sq.y)

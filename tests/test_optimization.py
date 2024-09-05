# -*- coding: utf-8 -*-

import os
import unittest
import numpy as np

from glassure import Pattern, convert_density_to_atoms_per_cubic_angstrom
from glassure.utility import (
    extrapolate_to_zero_poly,
    calculate_f_mean_squared,
    calculate_f_squared_mean,
    calculate_incoherent_scattering,
)
from glassure.transform import calculate_sq
from glassure.configuration import OptimizeConfig
from glassure.optimization import optimize_sq, optimize_density
from glassure.calc import calculate_pdf, create_calculate_pdf_configs
from glassure.methods import ExtrapolationMethod

from . import unittest_data_path

data_path_alloy = os.path.join(unittest_data_path, "Fe81S19.chi")
background_path_alloy = os.path.join(unittest_data_path, "Fe81S19_bkg.chi")

data_path_glass = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
background_path_glass = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


def test_optimize_sq():
    data = Pattern.from_file(data_path_alloy)
    background = Pattern.from_file(background_path_alloy)
    composition = {"Fe": 0.81, "S": 0.19}
    density = 7.9
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)
    f_squared_mean = calculate_f_squared_mean(composition, data.x)
    f_mean_squared = calculate_f_mean_squared(composition, data.x)
    incoherent_scattering = calculate_incoherent_scattering(composition, data.x)
    background_scaling = 0.97

    sample_pattern = data - background_scaling * background

    sq = calculate_sq(sample_pattern, f_squared_mean, f_mean_squared)
    sq = extrapolate_to_zero_poly(sq, np.min(sq.x) + 0.3)
    sq_optimized = optimize_sq(sq, 1.6, 5, atomic_density)
    assert not np.allclose(sq.y, sq_optimized.y)


def test_optimize_density():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density, density_error = optimize_density(data_config, calculation_config)

    assert density > 0
    assert density != 3.21
    assert density_error > 0


def test_optimize_density_x_range():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.2)

    density_1, density_error_1 = optimize_density(
        data_config, calculation_config, min_range=(0.3, 1.0)
    )

    density_2, density_error_2 = optimize_density(
        data_config, calculation_config, min_range=(0.3, 0.9)
    )

    assert density_1 != density_2


def test_optimize_density_method():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density_gr, _ = optimize_density(
        data_config, calculation_config, method="gr", min_range=(0.3, 1.0)
    )

    density_sq, _ = optimize_density(data_config, calculation_config, method="sq")

    assert density_gr != density_sq

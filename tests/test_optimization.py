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
from glassure.optimization import optimize_sq
from . import unittest_data_path

data_path = os.path.join(unittest_data_path, "Fe81S19.chi")
background_path = os.path.join(unittest_data_path, "Fe81S19_bkg.chi")


def test_optimize_sq():
    data = Pattern.from_file(data_path)
    background = Pattern.from_file(background_path)
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

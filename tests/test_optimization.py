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


class OptimizationTest(unittest.TestCase):
    def setUp(self):
        self.data_pattern = Pattern.from_file(data_path)
        self.background_pattern = Pattern.from_file(background_path)
        self.composition = {"Fe": 0.81, "S": 0.19}
        self.density = 7.9
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(
            self.composition, self.density
        )
        self.f_squared_mean = calculate_f_squared_mean(self.composition, self.data_pattern.x)
        self.f_mean_squared = calculate_f_mean_squared(self.composition, self.data_pattern.x)
        self.incoherent_scattering = calculate_incoherent_scattering(
            self.composition, self.data_pattern.x
        )
        self.background_scaling = 0.97

        self.sample_pattern = (
            self.data_pattern - self.background_scaling * self.background_pattern
        )

    def tearDown(self):
        pass

    def test_optimize_sq(self):
        sq = calculate_sq(self.sample_pattern, self.f_squared_mean, self.f_mean_squared)
        sq = extrapolate_to_zero_poly(sq, np.min(sq.x) + 0.3)
        sq_optimized = optimize_sq(sq, 1.6, 5, self.atomic_density)
        self.assertFalse(np.allclose(sq.y, sq_optimized.y))

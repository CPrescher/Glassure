__author__ = 'Clemens Prescher'

import os
import unittest
import numpy as np

from core import Pattern, convert_density_to_atoms_per_cubic_angstrom
from core.utility import extrapolate_to_zero_poly
from core.calc import calculate_sq
from core.optimization import optimize_sq

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
data_path = os.path.join(unittest_data_path, 'Fe81S19.chi')
background_path = os.path.join(unittest_data_path, 'Fe81S19_bkg.chi')


class OptimizationTest(unittest.TestCase):
    def setUp(self):
        self.data_spectrum = Pattern.from_file(data_path)
        self.background_spectrum = Pattern.from_file(background_path)
        self.composition = {'Fe': 0.81, 'S': 0.19}
        self.density = 7.9
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        self.background_scaling = 0.97

        self.sample_spectrum = self.data_spectrum - self.background_scaling * self.background_spectrum

    def tearDown(self):
        pass

    def test_optimize_sq(self):
        sq = calculate_sq(self.sample_spectrum, self.density, self.composition)
        sq = extrapolate_to_zero_poly(sq, np.min(sq.x)+0.3)
        sq_optimized = optimize_sq(sq, 1.6, 5, self.atomic_density)
        self.assertFalse(np.allclose(sq.y, sq_optimized.y))

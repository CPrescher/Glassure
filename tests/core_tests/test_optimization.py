# -*- coding: utf-8 -*-

import os
import unittest
import numpy as np

from glassure.core import Pattern, convert_density_to_atoms_per_cubic_angstrom
from glassure.core.utility import extrapolate_to_zero_poly
from glassure.core.transform import calculate_sq
from glassure.core.optimization import optimize_sq, optimize_soller_dac
from .. import unittest_data_path

data_path = os.path.join(unittest_data_path, 'Fe81S19.chi')
background_path = os.path.join(unittest_data_path, 'Fe81S19_bkg.chi')


class OptimizationTest(unittest.TestCase):
    def setUp(self):
        self.data_pattern = Pattern.from_file(data_path)
        self.background_pattern = Pattern.from_file(background_path)
        self.composition = {'Fe': 0.81, 'S': 0.19}
        self.density = 7.9
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        self.background_scaling = 0.97

        self.sample_pattern = self.data_pattern - self.background_scaling * self.background_pattern

    def tearDown(self):
        pass

    def test_optimize_sq(self):
        sq = calculate_sq(self.sample_pattern, self.density, self.composition)
        sq = extrapolate_to_zero_poly(sq, np.min(sq.x) + 0.3)
        sq_optimized = optimize_sq(sq, 1.6, 5, self.atomic_density)
        self.assertFalse(np.allclose(sq.y, sq_optimized.y))

    def test_optimize_soller_slit_dac(self):
        self.composition = {'Ar': 1}
        self.r = np.linspace(0.1, 10, 1000)

        sample_path = os.path.join(unittest_data_path, 'Argon_1GPa.chi')
        bkg_path = os.path.join(unittest_data_path, 'Argon_1GPa_bkg.chi')

        data_pattern = Pattern.from_file(sample_path)
        bkg_pattern = Pattern.from_file(bkg_path)
        self.data_pattern = Pattern(data_pattern.x / 10., data_pattern.y)
        self.bkg_pattern = Pattern(bkg_pattern.x / 10., bkg_pattern.y)

        initial_thickness = 0.1
        current_thickness = 0.05
        diamond_content = 30

        chi2, density, density_err, bkg_scaling, bkg_scaling_err, diamond_content, diamond_content_err = \
            optimize_soller_dac(
                self.data_pattern.limit(0.3, 9),
                self.bkg_pattern.limit(0.3, 9),
                self.composition,
                wavelength=0.37,
                initial_density=0.030,
                initial_bkg_scaling=0.55,
                initial_thickness=initial_thickness,
                sample_thickness=current_thickness,
                initial_carbon_content=diamond_content,
                r_cutoff=2.28,
                iterations=2,
                use_modification_fcn=True
            )

        # self.assertAlmostEqual(diamond_content, 0, places=5)
        self.assertAlmostEqual(bkg_scaling, 0.55, places=2)
        self.assertAlmostEqual(density, 0.026, places=2)

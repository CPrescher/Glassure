# -*- coding: utf8 -*-

import os
import unittest
import numpy as np

from core import Pattern, convert_density_to_atoms_per_cubic_angstrom
from core.utility import extrapolate_to_zero_poly
from core.calc import calculate_sq
from core.optimization import optimize_sq, optimize_soller_dac

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
        sq = extrapolate_to_zero_poly(sq, np.min(sq.x) + 0.3)
        sq_optimized = optimize_sq(sq, 1.6, 5, self.atomic_density)
        self.assertFalse(np.allclose(sq.y, sq_optimized.y))

    def test_optimize_soller_slit_dac(self):
        self.density = 1.9
        self.composition = {'Ar': 1}
        self.r = np.linspace(0.1, 10, 1000)

        sample_path = os.path.join(unittest_data_path, 'Argon_1GPa.chi')
        bkg_path = os.path.join(unittest_data_path, 'Argon_1GPa_bkg.chi')

        data_spectrum = Pattern.from_file(sample_path)
        bkg_spectrum = Pattern.from_file(bkg_path)
        self.data_spectrum = Pattern(data_spectrum.x / 10., data_spectrum.y)
        self.bkg_spectrum = Pattern(bkg_spectrum.x / 10., bkg_spectrum.y)

        bkg_scaling = 0.57

        self.q_min = 0.3
        self.q_max = 9.0

        self.sample_spectrum = self.data_spectrum - bkg_scaling * self.bkg_spectrum
        self.sample_spectrum = self.sample_spectrum.limit(self.q_min, self.q_max).extend_to(0, 0)

        initial_thickness = 0.1
        current_thickness = 0.05
        diamond_content = 10

        chi2, density, density_err, bkg_scaling, bkg_scaling_err, diamond_content, diamond_content_err = \
            optimize_soller_dac(
                self.data_spectrum.limit(0.3, 9),
                self.bkg_spectrum.limit(0.3, 9),
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

# -*- coding: utf-8 -*-

import unittest
import os

import numpy as np

from glassure.core import Pattern
from glassure.core.calc import calculate_normalization_factor, calculate_sq, calculate_fr, calculate_gr, calculate_sq_from_gr
from glassure.core.optimization import optimize_incoherent_container_scattering, optimize_sq
from glassure.core.calculator import StandardCalculator

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class GlassureCalculatorTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg': 2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

        self.data_pattern = Pattern()
        self.data_pattern.load(sample_path)

        self.bkg_pattern = Pattern()
        self.bkg_pattern.load(bkg_path)

        self.sample_pattern = self.data_pattern - self.bkg_pattern

        self.calculator = StandardCalculator(
            original_pattern=self.data_pattern,
            background_pattern=self.bkg_pattern,
            composition=self.composition,
            density=self.density,
            r=self.r
        )

    def compare_spectra(self, pattern1, pattern2):
        _, y1 = pattern1.data
        _, y2 = pattern2.data
        return np.array_equal(y1, y2)

    def test_normalization_factor_calculation(self):
        alpha_old = calculate_normalization_factor(self.sample_pattern, self.density, self.composition)
        alpha_new = self.calculator.get_normalization_factor()
        self.assertEqual(alpha_new, alpha_old)

    def test_sq_calculation(self):
        sq_pattern_old = calculate_sq(self.sample_pattern, self.density, self.composition)
        sq_pattern_new = self.calculator.calc_sq()

        _, y_old = sq_pattern_old.data
        _, y_new = sq_pattern_new.data

        self.assertTrue(np.array_equal(y_old, y_new))

    def test_fr_calculation(self):
        sq_pattern_old = calculate_sq(self.sample_pattern, self.density, self.composition)
        fr_pattern_old = calculate_fr(sq_pattern_old, r=self.r)
        fr_pattern_new = self.calculator.calc_fr(self.r)

        _, y_old = fr_pattern_old.data
        _, y_new = fr_pattern_new.data

        self.assertTrue(np.array_equal(y_old, y_new))

    def test_gr_calculation(self):
        sq_pattern_core = calculate_sq(self.sample_pattern, self.density, self.composition)
        fr_pattern_core = calculate_fr(sq_pattern_core, r=self.r)
        gr_pattern_core = calculate_gr(fr_pattern_core, self.density, self.composition)
        gr_pattern_calc = self.calculator.calc_gr()

        _, y_core = gr_pattern_core.data
        _, y_calc = gr_pattern_calc.data

        self.assertTrue(np.array_equal(y_core, y_calc))

    def test_optimize_sq(self):
        sq_pattern = calculate_sq(self.sample_pattern.limit(0, 24), self.density, self.composition)
        sq_pattern_optimized_core = optimize_sq(sq_pattern=sq_pattern,
                                                 r_cutoff=1.4,
                                                 iterations=5,
                                                 atomic_density=self.calculator.atomic_density)

        self.calculator = StandardCalculator(
            original_pattern=self.data_pattern.limit(0, 24),
            background_pattern=self.bkg_pattern.limit(0, 24),
            composition=self.composition,
            density=self.density,
            r=self.r
        )

        self.calculator.optimize_sq(1.4, 5)
        sq_pattern_optimized_calc = self.calculator.sq_pattern

        _, y_core = sq_pattern_optimized_core.data
        _, y_calc = sq_pattern_optimized_calc.data

        self.assertTrue(np.array_equal(y_core, y_calc))

    def test_calculate_sq_from_gr(self):
        sq_pattern = calculate_sq(self.sample_pattern, self.density, self.composition)
        sq_pattern = sq_pattern.limit(0, 24)
        fr_pattern = calculate_fr(sq_pattern)
        gr_pattern = calculate_gr(fr_pattern, self.density, self.composition)

        q, sq = sq_pattern.data

        calculate_sq_from_gr(gr_pattern, q, self.density, self.composition)

    def test_optimize_container_background(self):
        res = optimize_incoherent_container_scattering(self.sample_pattern,
                                                       sample_density=self.density,
                                                       sample_composition=self.composition,
                                                       container_composition={'C': 1},
                                                       r_cutoff=1.5)
        print(res)

# -*- coding: utf8 -*-

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

        self.data_spectrum = Pattern()
        self.data_spectrum.load(sample_path)

        self.bkg_spectrum = Pattern()
        self.bkg_spectrum.load(bkg_path)

        self.sample_spectrum = self.data_spectrum - self.bkg_spectrum

        self.calculator = StandardCalculator(
            original_spectrum=self.data_spectrum,
            background_spectrum=self.bkg_spectrum,
            composition=self.composition,
            density=self.density,
            r=self.r
        )

    def compare_spectra(self, spectrum1, spectrum2):
        _, y1 = spectrum1.data
        _, y2 = spectrum2.data
        return np.array_equal(y1, y2)

    def test_normalization_factor_calculation(self):
        alpha_old = calculate_normalization_factor(self.sample_spectrum, self.density, self.composition)
        alpha_new = self.calculator.get_normalization_factor()
        self.assertEqual(alpha_new, alpha_old)

    def test_sq_calculation(self):
        sq_spectrum_old = calculate_sq(self.sample_spectrum, self.density, self.composition)
        sq_spectrum_new = self.calculator.calc_sq()

        _, y_old = sq_spectrum_old.data
        _, y_new = sq_spectrum_new.data

        self.assertTrue(np.array_equal(y_old, y_new))

    def test_fr_calculation(self):
        sq_spectrum_old = calculate_sq(self.sample_spectrum, self.density, self.composition)
        fr_spectrum_old = calculate_fr(sq_spectrum_old, r=self.r)
        fr_spectrum_new = self.calculator.calc_fr(self.r)

        _, y_old = fr_spectrum_old.data
        _, y_new = fr_spectrum_new.data

        self.assertTrue(np.array_equal(y_old, y_new))

    def test_gr_calculation(self):
        sq_spectrum_core = calculate_sq(self.sample_spectrum, self.density, self.composition)
        fr_spectrum_core = calculate_fr(sq_spectrum_core, r=self.r)
        gr_spectrum_core = calculate_gr(fr_spectrum_core, self.density, self.composition)
        gr_spectrum_calc = self.calculator.calc_gr()

        _, y_core = gr_spectrum_core.data
        _, y_calc = gr_spectrum_calc.data

        self.assertTrue(np.array_equal(y_core, y_calc))

    def test_optimize_sq(self):
        sq_spectrum = calculate_sq(self.sample_spectrum.limit(0, 24), self.density, self.composition)
        sq_spectrum_optimized_core = optimize_sq(sq_spectrum=sq_spectrum,
                                                 r_cutoff=1.4,
                                                 iterations=5,
                                                 atomic_density=self.calculator.atomic_density)

        self.calculator = StandardCalculator(
            original_spectrum=self.data_spectrum.limit(0, 24),
            background_spectrum=self.bkg_spectrum.limit(0, 24),
            composition=self.composition,
            density=self.density,
            r=self.r
        )

        self.calculator.optimize_sq(1.4, 5)
        sq_spectrum_optimized_calc = self.calculator.sq_spectrum

        _, y_core = sq_spectrum_optimized_core.data
        _, y_calc = sq_spectrum_optimized_calc.data

        self.assertTrue(np.array_equal(y_core, y_calc))

    def test_calculate_sq_from_gr(self):
        sq_spectrum = calculate_sq(self.sample_spectrum, self.density, self.composition)
        sq_spectrum = sq_spectrum.limit(0, 24)
        fr_spectrum = calculate_fr(sq_spectrum)
        gr_spectrum = calculate_gr(fr_spectrum, self.density, self.composition)

        q, sq = sq_spectrum.data

        calculate_sq_from_gr(gr_spectrum, q, self.density, self.composition)

    def test_optimize_container_background(self):
        res = optimize_incoherent_container_scattering(self.sample_spectrum,
                                                       sample_density=self.density,
                                                       sample_composition=self.composition,
                                                       container_composition={'C': 1},
                                                       r_cutoff=1.5)
        print(res)

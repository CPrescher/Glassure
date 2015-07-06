# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import os

import numpy as np

from core import Spectrum
from core.calc import calculate_normalization_factor, calculate_sq, calculate_fr, calculate_gr
from core.calculator import StandardCalculator

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class GlassureCalculatorTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg':2, 'Si':1, 'O':4}
        self.r = np.linspace(0.1,10,1000)


        self.data_spectrum = Spectrum()
        self.data_spectrum.load(sample_path)

        self.bkg_spectrum = Spectrum()
        self.bkg_spectrum.load(bkg_path)

        self.sample_spectrum = self.data_spectrum - self.bkg_spectrum

        self.calculator = StandardCalculator(
            original_spectrum=self.data_spectrum,
            background_spectrum=self.bkg_spectrum,
            elemental_abundances=self.composition,
            density =self.density,
            r = self.r
        )

    def compare_spectra(self, spectrum1, spectrum2):
        _, y1 = spectrum1.data
        _, y2 = spectrum2.data
        print np.sum(np.abs(y1-y2))
        return np.array_equal(y1, y2)

    def test_normalization_factor_calculation(self):
        alpha_old = calculate_normalization_factor(self.sample_spectrum, self.density, self.composition)
        alpha_new = self.calculator.get_normalization_factor()
        self.assertEqual(alpha_new, alpha_old)

    def test_sq_calculation(self):
        sq_spectrum_old = calculate_sq(self.sample_spectrum,self.density, self.composition)
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





# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import numpy as np
import os

from Models.Spectrum import Spectrum
from Models.GlassureCalculator import StandardCalculator

unittest_data_path = os.path.join(os.path.dirname(__file__), 'TestData')


class GlassureCalculatorTest(unittest.TestCase):
    def setUp(self):
        self.bkg_scaling=0.83133015
        self.density = 1.7
        self.composition = {'Mg':2, 'Si':1, 'O':4}
        self.r = np.linspace(0.1,10,1000)


        self.data_spectrum = Spectrum()
        self.data_spectrum.load('TestData/Mg2SiO4_091.xy')
        self.data_spectrum.set_smoothing(5)

        self.bkg_spectrum = Spectrum()
        self.bkg_spectrum.load('TestData/Mg2SiO4_091_bkg.xy')
        self.bkg_spectrum.set_smoothing(5)

        self.sample_spectrum = self.data_spectrum - self.bkg_scaling*self.bkg_spectrum


        self.calculator = StandardCalculator(
            original_spectrum=self.data_spectrum,
            background_spectrum=self.bkg_spectrum,
            background_scaling=self.bkg_scaling,
            elemental_abundances=self.composition,
            density =self.density,
            r = self.r
        )


    def tearDown(self):
        pass

    def compare_spectra(self, spectrum1, spectrum2):
        _, y1 = spectrum1.data
        _, y2 = spectrum2.data
        print np.sum(np.abs(y1-y2))
        return np.array_equal(y1, y2)

    def test_normalization_factor_calculation(self):
        alpha_old = calculate_normalization_factor(self.composition,self.density, self.sample_spectrum)
        alpha_new = self.calculator.get_normalization_factor()
        self.assertEqual(alpha_new, alpha_old)

    def test_sq_calculation(self):
        sq_spectrum_old = calc_sq(self.data_spectrum, self.bkg_spectrum, self.bkg_scaling,
                                  self.composition, self.density)
        sq_spectrum_new = self.calculator.calc_sq()

        _, y_old = sq_spectrum_old.data
        _, y_new = sq_spectrum_new.data

        self.assertTrue(np.array_equal(y_old, y_new))

    def test_all_calculations(self):
        sq_spectrum_old, fr_spectrum_old, gr_spectrum_old = calc_transforms(
            self.data_spectrum,
            self.bkg_spectrum,
            self.bkg_scaling,
            self.composition,
            self.density,
            self.r
        )

        self.assertTrue(self.compare_spectra(sq_spectrum_old, self.calculator.sq_spectrum))
        self.assertTrue(self.compare_spectra(fr_spectrum_old, self.calculator.fr_spectrum))
        self.assertTrue(self.compare_spectra(gr_spectrum_old, self.calculator.gr_spectrum))




# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
import unittest
from Spectrum import Spectrum
import numpy as np


class SpectrumTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_plus_and_minus_operators(self):
        x = np.linspace(0, 10, 100)
        spectrum1 = Spectrum(x, np.sin(x))
        spectrum2 = Spectrum(x, np.sin(x))

        spectrum3 = spectrum1+spectrum2
        self.assertTrue(np.array_equal(spectrum3._y, np.sin(x)*2))
        self.assertTrue(np.array_equal(spectrum2._y, np.sin(x)*1))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))

        spectrum3 = spectrum1+spectrum1
        self.assertTrue(np.array_equal(spectrum3._y, np.sin(x)*2))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))

        spectrum3 = spectrum2-spectrum1
        self.assertTrue(np.array_equal(spectrum3._y, np.sin(x)*0))
        self.assertTrue(np.array_equal(spectrum2._y, np.sin(x)*1))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))

        spectrum3 = spectrum1-spectrum1
        self.assertTrue(np.array_equal(spectrum3._y, np.sin(x)*0))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))
        self.assertTrue(np.array_equal(spectrum1._y, np.sin(x)*1))

    def test_multiply_operator(self):
        x = np.linspace(0, 10, 100)
        spectrum1 = 2*Spectrum(x, np.sin(x))

        spectrum2 = 2*Spectrum(x, np.sin(x))

        self.assertTrue(np.array_equal(spectrum2._y, np.sin(x)*2))

    def test_equality_operator(self):
        x = np.linspace(0, 10, 100)
        spectrum1 = Spectrum(x, np.sin(x))
        spectrum2 = Spectrum(x, np.sin(2*x))

        self.assertTrue(spectrum1 == spectrum1)
        self.assertFalse(spectrum1 == spectrum2)

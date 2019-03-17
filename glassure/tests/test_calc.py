# -*- coding: utf8 -*-

import os
import unittest
import numpy as np

from glassure.core import Pattern, calculate_sq
from glassure.core.optimization import optimize_sq
from glassure.core.calc import calculate_normalization_factor, fit_normalization_factor, calculate_fr
from glassure.core.utility import convert_density_to_atoms_per_cubic_angstrom

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class CalcTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg': 2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

        self.data_spectrum = Pattern()
        self.data_spectrum.load(sample_path)

        self.bkg_spectrum = Pattern()
        self.bkg_spectrum.load(bkg_path)

        self.sample_spectrum = self.data_spectrum - self.bkg_spectrum

    def test_fit_normalization_factor(self):
        n_integral = calculate_normalization_factor(self.sample_spectrum.limit(0, 20),
                                                    self.density,
                                                    self.composition)

        n_fit = fit_normalization_factor(self.sample_spectrum.limit(0, 20), self.composition)

        self.assertAlmostEqual(n_integral, n_fit, places=2)

    def test_fft_implementation_of_calculate_fr(self):
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        sq = calculate_sq(self.sample_spectrum.limit(0, 20), self.density, self.composition).extend_to(0, 0)

        sq = optimize_sq(sq, 1.4, 5, atomic_density)

        fr_int = calculate_fr(sq, method='integral')
        fr_fft = calculate_fr(sq, method='fft')

        self.assertAlmostEqual(np.mean((fr_int.y - fr_fft.y)**2),
                               0,
                               places=5)

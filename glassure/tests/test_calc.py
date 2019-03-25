# -*- coding: utf-8 -*-

import os
import unittest
import numpy as np

from glassure.core import Pattern, calculate_sq
from glassure.core.optimization import optimize_sq
from glassure.core.calc import calculate_normalization_factor, fit_normalization_factor, calculate_fr, \
    calculate_sq_from_fr, calculate_gr, calculate_sq_from_gr
from glassure.core.utility import convert_density_to_atoms_per_cubic_angstrom

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class CalcTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg': 2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

        self.data_pattern = Pattern()
        self.data_pattern.load(sample_path)

        self.bkg_pattern = Pattern()
        self.bkg_pattern.load(bkg_path)

        self.sample_pattern = self.data_pattern - self.bkg_pattern

    def test_fit_normalization_factor(self):
        n_integral = calculate_normalization_factor(self.sample_pattern.limit(0, 20),
                                                    self.density,
                                                    self.composition)

        n_fit = fit_normalization_factor(self.sample_pattern.limit(0, 20), self.composition)

        self.assertAlmostEqual(n_integral, n_fit, places=2)

    def test_fft_implementation_of_calculate_fr(self):
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        sq = calculate_sq(self.sample_pattern.limit(0, 20), self.density, self.composition).extend_to(0, 0)

        sq = optimize_sq(sq, 1.4, 5, atomic_density)

        fr_int = calculate_fr(sq, method='integral')
        fr_fft = calculate_fr(sq, method='fft')

        self.assertAlmostEqual(np.mean((fr_int.y - fr_fft.y) ** 2),
                               0,
                               places=5)

    def test_calculate_sq_from_fr_using_fft(self):
        sq = calculate_sq(self.sample_pattern.limit(0, 20), self.density, self.composition).extend_to(0, 0)

        fr_fft = calculate_fr(sq, r=np.arange(0, 100, 0.01), method='fft')
        sq_fft = calculate_sq_from_fr(fr_fft, sq.x, method='fft')

        self.assertAlmostEqual(np.mean((sq_fft-sq).limit(5, 20).y**2), 0, places=5)

    def test_calculate_sq_from_fr_using_integral(self):
        sq = calculate_sq(self.sample_pattern.limit(0, 20), self.density, self.composition).extend_to(0, 0)

        fr_fft = calculate_fr(sq, r=np.arange(0, 100, 0.01), method='integral')
        sq_fft = calculate_sq_from_fr(fr_fft, sq.x, method='integral')

        self.assertAlmostEqual(np.mean((sq_fft-sq).limit(5, 20).y**2), 0, places=5)

    def test_calculate_sq_from_gr_using_fft(self):
        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        sq = calculate_sq(self.sample_pattern.limit(0, 20), self.density, self.composition).extend_to(0, 0)
        sq = optimize_sq(sq, 1.4, 5, atomic_density)

        fr_fft = calculate_fr(sq, r=np.arange(0, 100, 0.01), method='fft')
        gr_fft = calculate_gr(fr_fft, self.density, self.composition)

        sq_fft = calculate_sq_from_gr(gr_fft, sq.x, self.density, self.composition, method='fft')

        self.assertAlmostEqual(np.mean((sq_fft-sq).limit(5, 20).y**2), 0, places=5)
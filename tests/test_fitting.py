# -*- coding: utf-8 -*-

import unittest
import numpy as np

from glassure.fitting import i_q_peak, t_r_peak, t_r_peak_gaussian
from glassure.utility import calculate_weighting_factor_wkm


class FittingTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg':2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

    def test_i_q_peak(self):
        q = np.linspace(0, 10, 1001)
        q[0] = 1e-10
        peak = i_q_peak(q, 4, 1.6, 0.1, self.composition, 'Si', 'O')
        self.assertEqual(len(peak), len(q))

    def test_t_r_peak(self):
        q = np.linspace(0.01, 10, 1001)
        peak = t_r_peak(self.r, 4, 1.6, 0.15, self.composition, 'Si', 'O', q)
        self.assertEqual(len(peak), len(self.r))

    def test_t_r_peak_gaussian(self):
        r = np.linspace(0.1, 10, 1001)
        peak = t_r_peak_gaussian(r, 4, 1.6, 0.15, self.composition, 'Si', 'O')
        self.assertEqual(len(peak), len(r))

    def test_t_r_peak_gaussian_recovers_coordination_number(self):
        r = np.linspace(0.01, 5, 20000)
        q = np.linspace(0.5, 18, 1000)
        coordination_number = 4.0
        peak = t_r_peak_gaussian(
            r,
            coordination_number,
            1.6,
            0.15,
            self.composition,
            'Si',
            'O',
            q,
        )
        c_2 = self.composition['O'] / sum(self.composition.values())
        weight = calculate_weighting_factor_wkm(
            self.composition, 'Si', 'O', q
        )
        trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
        recovered_coordination_number = c_2 / weight * trapezoid(r * peak, r)

        self.assertAlmostEqual(
            recovered_coordination_number, coordination_number, places=6
        )

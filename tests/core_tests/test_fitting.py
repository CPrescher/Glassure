# -*- coding: utf-8 -*-

import unittest
import numpy as np

from glassure.core.fitting import i_q_peak, t_r_peak


class FittingTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg':2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

    def test_i_q_peak(self):
        q = np.linspace(0, 10, 1001)
        peak = i_q_peak(q, 4, 1.6, 0.1, self.composition, 'Si', 'O')
        self.assertEqual(len(peak), len(q))

    def test_t_r_peak(self):
        q = np.linspace(0.01, 10, 1001)
        peak = t_r_peak(self.r, 4, 1.6, 0.15, self.composition, 'Si', 'O', q)
        self.assertEqual(len(peak), len(self.r))

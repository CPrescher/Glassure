# -*- coding: utf8 -*-

import unittest

import numpy as np

from core import SollerCorrection
from core.soller_correction import calculate_angles


class SollerCorrectionTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_dispersion_angle_map(self):
        two_theta = np.linspace(1, 40, 200)
        soller = SollerCorrection(two_theta, 0.3)
        self.assertTrue(np.sum(soller.dispersion_angle_map.X) > 0)

        self.assertEqual(soller.dispersion_angle_map.X.shape, soller.dispersion_angle_map.Y.shape)
        self.assertEqual(soller.dispersion_angle_map.X.shape, soller.dispersion_angle_map.data.shape)

        self.assertEqual(np.min(soller.dispersion_angle_map.X), 1)
        self.assertEqual(np.max(soller.dispersion_angle_map.X), 40)

        self.assertEqual(np.min(soller.dispersion_angle_map.Y), -0.15)
        self.assertEqual(np.max(soller.dispersion_angle_map.Y), 0.15)

    def test_calculate_function_for_region(self):
        two_theta = np.linspace(1, 40, 200)
        soller = SollerCorrection(two_theta, 0.1)
        sample_transfer = soller.transfer_function_from_region(-0.025, 0.025)
        self.assertEqual(two_theta.shape, sample_transfer.shape)

    def test_calculate_sample_transfer_function(self):
        two_theta = np.linspace(1, 40, 200)
        soller = SollerCorrection(two_theta, 0.1)
        sample_transfer = soller.transfer_function_sample(0.5)
        self.assertEqual(two_theta.shape, sample_transfer.shape)

    def test_calculate_angles_for_single_values(self):
        p1 = [0, 1]
        p2 = [1, 0]
        c = [0, 0]

        angle = calculate_angles(p1, p2, c)
        self.assertAlmostEqual(angle, np.pi / 2)

    def test_calculat_angles_for_multiple_centers(self):
        p1 = [0, 1]
        p2 = [1, 0]
        c_x = np.linspace(-0.5, 0.5)
        c = [c_x, np.zeros_like(c_x)]

        angles = calculate_angles(p1, p2, c)
        self.assertAlmostEqual(len(angles), len(c_x))

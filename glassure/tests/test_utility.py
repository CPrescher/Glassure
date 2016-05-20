# -*- coding: utf8 -*-

import unittest
import numpy as np

from core.utility import normalize_composition, convert_density_to_atoms_per_cubic_angstrom, \
    calculate_f_mean_squared, calculate_f_squared_mean, calculate_incoherent_scattering, \
    extrapolate_to_zero_linear, extrapolate_to_zero_poly, extrapolate_to_zero_spline, \
    convert_two_theta_to_q_space, convert_two_theta_to_q_space_raw
from core import Pattern


class UtilityTest(unittest.TestCase):
    def test_normalize_elemental_abundances(self):
        composition = {'Si': 1, 'O': 2}
        norm_composition = normalize_composition(composition)
        self.assertEqual(norm_composition, {'Si': 1 / 3., 'O': 2 / 3.})

        composition = {'Na': 2, 'Si': 2, 'O': 5}
        norm_composition = normalize_composition(composition)
        self.assertEqual(norm_composition, {'Na': 2. / 9, 'Si': 2 / 9., 'O': 5 / 9.})

    def test_convert_density_to_atoms_per_cubic_angstrom(self):
        density = 2.2
        composition = {'Si': 1, 'O': 2}
        density_au = convert_density_to_atoms_per_cubic_angstrom(composition, density)

        self.assertAlmostEqual(density_au, 0.0662, places=4)

    def test_calculate_f_mean_squared(self):
        q = np.linspace(0, 10)
        composition = {'Si': 1, 'O': 2}

        f_mean_squared = calculate_f_mean_squared(composition, q)

        self.assertEqual(len(q), len(f_mean_squared))

        si_f = calculate_f_mean_squared({'Si': 1}, q) ** 0.5
        o_f = calculate_f_mean_squared({'O': 1}, q) ** 0.5

        f_mean_squared_hand = (1 / 3. * si_f + 2 / 3. * o_f) ** 2

        self.assertTrue(np.array_equal(f_mean_squared, f_mean_squared_hand))

    def test_calculate_f_squared_mean(self):
        q = np.linspace(0, 10)
        composition = {'Si': 1, 'O': 2}

        f_squared_mean = calculate_f_squared_mean(composition, q)

        self.assertEqual(len(q), len(f_squared_mean))

        si_f = calculate_f_squared_mean({'Si': 1}, q) ** 0.5
        o_f = calculate_f_squared_mean({'O': 1}, q) ** 0.5

        f_squared_mean_hand = 1 / 3. * si_f ** 2 + 2 / 3. * o_f ** 2

        self.assertTrue(np.array_equal(f_squared_mean, f_squared_mean_hand))

    def test_calculate_incoherent_scattering(self):
        q = np.linspace(0, 10)
        incoherent_scattering = calculate_incoherent_scattering({'Si': 1, 'O': 2}, q)

        self.assertEqual(len(q), len(incoherent_scattering))

    def test_linear_extrapolation(self):
        x = np.arange(1, 5.05, 0.05)
        y = np.ones(len(x))
        spectrum = Pattern(x, y)

        extrapolated_spectrum = extrapolate_to_zero_linear(spectrum)

        x1, y1 = extrapolated_spectrum.data

        self.assertLess(x1[0], x[0])
        self.assertLess(y1[1], y[1])

        x_linear = x1[x1 < 1]
        y_linear = y1[x1 < 1]
        self.assertAlmostEqual(np.sum(y_linear - x_linear), 0)

    def test_extrapolate_to_zero_spline(self):
        x = np.arange(1, 5.05, 0.05)
        y = -2 + x * 0.2

        spectrum = Pattern(x, y)

        extrapolated_spectrum = extrapolate_to_zero_spline(spectrum, 2)

    def test_extrapolate_to_zero_poly(self):
        a = 0.3
        b = 0.1
        c = 0.1
        x_max = 3

        x = np.arange(1, 5.05, 0.05)
        y = a * (x - c) + b * (x - c) ** 2
        spectrum = Pattern(x, y)

        extrapolated_spectrum = extrapolate_to_zero_poly(spectrum, x_max)
        x1, y1 = extrapolated_spectrum.data

        x_extrapolate = x1[x1 < 1]
        y_extrapolate = y1[x1 < 1]

        y_expected = a * (x_extrapolate - c) + b * (x_extrapolate - c) ** 2
        y_expected[x_extrapolate < c] = 0

        self.assertAlmostEqual(np.sum(y_extrapolate - y_expected), 0)

        extrapolated_spectrum = extrapolate_to_zero_poly(spectrum, x_max, replace=True)
        x1, y1 = extrapolated_spectrum.data

        x_extrapolate = x1[x1 < 1]
        y_extrapolate = y1[x1 < 1]

        y_expected = a * (x_extrapolate - c) + b * (x_extrapolate - c) ** 2
        y_expected[x_extrapolate < c] = 0

        self.assertAlmostEqual(np.sum(y_extrapolate - y_expected), 0)

    def test_convert_two_theta_to_q_space(self):
        data_theta = np.linspace(0, 25)
        wavelength = 0.31
        data_q = convert_two_theta_to_q_space_raw(data_theta, wavelength)

        self.assertLess(np.max(data_q), 10)
        self.assertAlmostEqual(np.max(data_q), 4 * np.pi * np.sin(25. / 360 * np.pi) / wavelength)

        spectrum_theta = Pattern(data_theta, np.ones(data_theta.shape))
        spectrum_q = convert_two_theta_to_q_space(spectrum_theta, wavelength)

        self.assertLess(np.max(spectrum_q.x), 10)
        self.assertAlmostEqual(np.max(spectrum_q.x), 4 * np.pi * np.sin(25. / 360 * np.pi) / wavelength)

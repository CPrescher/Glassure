# -*- coding: utf-8 -*-
import unittest
import numpy as np

from glassure.core.utility import (
    normalize_composition,
    convert_density_to_atoms_per_cubic_angstrom,
    calculate_f_mean_squared,
    calculate_f_squared_mean,
    calculate_incoherent_scattering,
    extrapolate_to_zero_linear,
    extrapolate_to_zero_poly,
    extrapolate_to_zero_spline,
    extrapolate_to_zero_step,
    convert_two_theta_to_q_space,
    convert_two_theta_to_q_space_raw,
    calculate_s0,
)
from glassure.core import Pattern


class UtilityTest(unittest.TestCase):
    def test_normalize_elemental_abundances(self):
        composition = {"Si": 1, "O": 2}
        norm_composition = normalize_composition(composition)
        self.assertEqual(norm_composition, {"Si": 1 / 3.0, "O": 2 / 3.0})

        composition = {"Na": 2, "Si": 2, "O": 5}
        norm_composition = normalize_composition(composition)
        self.assertEqual(norm_composition, {"Na": 2.0 / 9, "Si": 2 / 9.0, "O": 5 / 9.0})

    def test_convert_density_to_atoms_per_cubic_angstrom(self):
        density = 2.2
        composition = {"Si": 1, "O": 2}
        density_au = convert_density_to_atoms_per_cubic_angstrom(composition, density)

        self.assertAlmostEqual(density_au, 0.0662, places=4)

    def test_calculate_f_mean_squared(self):
        q = np.linspace(0, 10)
        composition = {"Si": 1, "O": 2}

        f_mean_squared = calculate_f_mean_squared(composition, q)

        self.assertEqual(len(q), len(f_mean_squared))

        si_f = calculate_f_mean_squared({"Si": 1}, q) ** 0.5
        o_f = calculate_f_mean_squared({"O": 1}, q) ** 0.5

        f_mean_squared_hand = (1 / 3.0 * si_f + 2 / 3.0 * o_f) ** 2

        self.assertTrue(np.array_equal(f_mean_squared, f_mean_squared_hand))

    def test_calculate_f_squared_mean(self):
        q = np.linspace(0, 10)
        composition = {"Si": 1, "O": 2}

        f_squared_mean = calculate_f_squared_mean(composition, q)

        self.assertEqual(len(q), len(f_squared_mean))

        si_f = calculate_f_squared_mean({"Si": 1}, q) ** 0.5
        o_f = calculate_f_squared_mean({"O": 1}, q) ** 0.5

        f_squared_mean_hand = 1 / 3.0 * si_f**2 + 2 / 3.0 * o_f**2

        self.assertTrue(np.array_equal(f_squared_mean, f_squared_mean_hand))

    def test_calculate_S0(self):
        S0 = calculate_s0({"Si": 1, "O": 2})
        self.assertLess(S0, 0)

        S0 = calculate_s0({"Ge": 1, "O": 2})
        self.assertLess(S0, -0.4)

        S0 = calculate_s0({"H": 2, "O": 1}, sf_source="brown_hubbell")
        self.assertLess(S0, -0.8)

    def test_calculate_incoherent_scattering(self):
        q = np.linspace(0, 10)
        incoherent_scattering = calculate_incoherent_scattering({"Si": 1, "O": 2}, q)

        self.assertEqual(len(q), len(incoherent_scattering))

    def test_step_extrapolation(self):
        x = np.arange(1, 5.05, 0.05)
        y = -2 + x * 0.2
        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_step(pattern)
        x1, y1 = extrapolated_pattern.data

        self.assertLess(x1[0], x[0])
        self.assertEqual(y1[0], 0)

    def test_step_extrapolation_with_different_y(self):
        x = np.arange(1, 5.05, 0.05)
        y = -2 + x * 0.2
        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_step(pattern, -2)
        x1, y1 = extrapolated_pattern.data

        self.assertLess(x1[0], x[0])
        self.assertAlmostEqual(y1[x1 < x[0]][-1], -2)

        self.assertEqual(y1[0], -2)

    def test_linear_extrapolation(self):
        x = np.arange(1, 5.05, 0.05)
        y = np.ones(len(x))
        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_linear(pattern)

        x1, y1 = extrapolated_pattern.data

        self.assertLess(x1[0], x[0])
        self.assertLess(y1[1], y[1])

        x_linear = x1[x1 < 1]
        y_linear = y1[x1 < 1]
        self.assertAlmostEqual(np.sum(y_linear - x_linear), 0)

    def test_linear_extrapolation_with_different_y(self):
        x = np.arange(1, 5.05, 0.05)
        y = -2 + x * 0.2
        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_linear(pattern, -2)
        x1, y1 = extrapolated_pattern.data

        self.assertAlmostEqual(y1[0], x1[0] * 0.2 - 2)

    def test_extrapolate_to_zero_spline(self):
        x = np.arange(1, 5.05, 0.05)
        y = x**2 * 0.2

        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_spline(pattern, 2)
        x1, y1 = extrapolated_pattern.data

        self.assertLess(x1[0], x[0])
        self.assertAlmostEqual(y1[0], 0)

    def test_extrapolate_to_zero_spline_with_different_y(self):
        x = np.arange(1, 5.05, 0.05)
        y = x**2 * 0.2 - 2

        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_spline(pattern, 2, y0=-2)
        x1, y1 = extrapolated_pattern.data

        self.assertLess(x1[0], x[0])
        self.assertAlmostEqual(y1[0], -2)

    def test_extrapolate_to_zero_poly(self):
        a = 0.3
        b = 0.1
        c = 0.1
        x_max = 3

        x = np.arange(1, 5.05, 0.05)
        y = a * (x - c) + b * (x - c) ** 2
        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_poly(pattern, x_max)
        x1, y1 = extrapolated_pattern.data

        x_extrapolate = x1[x1 < 1]
        y_extrapolate = y1[x1 < 1]

        y_expected = a * (x_extrapolate - c) + b * (x_extrapolate - c) ** 2
        y_expected[x_extrapolate < c] = 0

        self.assertAlmostEqual(np.sum(y_extrapolate - y_expected), 0)

        extrapolated_pattern = extrapolate_to_zero_poly(pattern, x_max, replace=True)
        x1, y1 = extrapolated_pattern.data

        x_extrapolate = x1[x1 < 1]
        y_extrapolate = y1[x1 < 1]

        y_expected = a * (x_extrapolate - c) + b * (x_extrapolate - c) ** 2
        y_expected[x_extrapolate < c] = 0

        self.assertAlmostEqual(np.sum(y_extrapolate - y_expected), 0)

    def test_extrapolate_to_zero_poly_with_different_y(self):
        x = np.arange(1, 5.05, 0.05)
        y = x**2 * 0.2 - 0.3

        pattern = Pattern(x, y)

        extrapolated_pattern = extrapolate_to_zero_poly(pattern, 2, y0=-0.2)
        x1, y1 = extrapolated_pattern.data

        self.assertAlmostEqual(y1[0], -0.2)
        self.assertAlmostEqual(y1[5], -0.2)

    def test_convert_two_theta_to_q_space(self):
        data_theta = np.linspace(0, 25)
        wavelength = 0.31
        data_q = convert_two_theta_to_q_space_raw(data_theta, wavelength)

        self.assertLess(np.max(data_q), 10)
        self.assertAlmostEqual(
            np.max(data_q), 4 * np.pi * np.sin(25.0 / 360 * np.pi) / wavelength
        )

        pattern_theta = Pattern(data_theta, np.ones(data_theta.shape))
        pattern_q = convert_two_theta_to_q_space(pattern_theta, wavelength)

        self.assertLess(np.max(pattern_q.x), 10)
        self.assertAlmostEqual(
            np.max(pattern_q.x), 4 * np.pi * np.sin(25.0 / 360 * np.pi) / wavelength
        )

# -*- coding: utf-8 -*-
import unittest

import numpy as np

from glassure.core import Pattern


class PatternTest(unittest.TestCase):
    def test_plus_and_minus_operators(self):
        x = np.linspace(0, 10, 100)
        pattern1 = Pattern(x, np.sin(x))
        pattern2 = Pattern(x, np.sin(x))

        pattern3 = pattern1 + pattern2
        self.assertTrue(np.array_equal(pattern3._y, np.sin(x) * 2))
        self.assertTrue(np.array_equal(pattern2._y, np.sin(x) * 1))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))

        pattern3 = pattern1 + pattern1
        self.assertTrue(np.array_equal(pattern3._y, np.sin(x) * 2))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))

        pattern3 = pattern2 - pattern1
        self.assertTrue(np.array_equal(pattern3._y, np.sin(x) * 0))
        self.assertTrue(np.array_equal(pattern2._y, np.sin(x) * 1))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))

        pattern3 = pattern1 - pattern1
        self.assertTrue(np.array_equal(pattern3._y, np.sin(x) * 0))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))
        self.assertTrue(np.array_equal(pattern1._y, np.sin(x) * 1))

    def test_multiply_operator(self):
        x = np.linspace(0, 10, 100)
        pattern = 2 * Pattern(x, np.sin(x))

        self.assertTrue(np.array_equal(pattern._y, np.sin(x) * 2))

    def test_equality_operator(self):
        x = np.linspace(0, 10, 100)
        pattern1 = Pattern(x, np.sin(x))
        pattern2 = Pattern(x, np.sin(2 * x))

        self.assertTrue(pattern1 == pattern1)
        self.assertFalse(pattern1 == pattern2)

    def test_binning(self):
        x = np.linspace(2.8, 10.8, 100)

        pattern = Pattern(x, np.sin(x))

        binned_pattern = pattern.rebin(1)

        self.assertTrue(np.sum(binned_pattern.y), np.sum(pattern.y))
        # self.assertLessEqual(np.min(binned_pattern.x), np.min(x))
        # self.assertEqual(np.min(np.min(binned_)))
        print(binned_pattern.x)
        print(binned_pattern.y)

    def test_extend_to(self):
        x = np.arange(2.8, 10, 0.2)

        pattern = Pattern(x, x - 2)
        extended_pattern = pattern.extend_to(0, 0)

        self.assertEqual(np.sum(extended_pattern.limit(0, 2.7).y), 0)
        self.assertAlmostEqual(extended_pattern.x[0], 0)

        pos_extended_pattern = pattern.extend_to(20, 5)

        self.assertEqual(np.mean(pos_extended_pattern.limit(10.1, 21).y), 5)
        self.assertAlmostEqual(pos_extended_pattern.x[-1], 20)

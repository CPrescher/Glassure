# -*- coding: utf8 -*-

__author__ = 'Clemens Prescher'

import unittest
import os
import numpy as np
import matplotlib.pyplot as plt

from ScatteringFactors import *


class ScatteringFactorsTest(unittest.TestCase):
    def setUp(self):
        self.q = np.linspace(1, 12, 1000)
        self.form_factor_vitali = {
            'Si': 3.7464 * np.exp(-1.3104 * (self.q / 4 / np.pi) ** 2) + 1.4345 + 4.2959 * np.exp(
                -2.8652 * (self.q / 4 / np.pi) ** 2) + 3.5786 * np.exp(
                -36.3701 * (self.q / 4 / np.pi) ** 2) + .9544 * np.exp(
                -97.9643 * (self.q / 4 / np.pi) ** 2),
            'O': 1.3721 * np.exp(-.387 * (self.q / 4 / np.pi) ** 2) + .4348 + 2.0624 * np.exp(
                -5.5416 * (self.q / 4 / np.pi) ** 2) + 3.0566 * np.exp(
                -12.332 * (self.q / 4 / np.pi) ** 2) + 1.0743 * np.exp(
                -29.88 * (self.q / 4 / np.pi) ** 2),
            'Mg': 1.7214 * np.exp(-.5091 * (self.q / 4 / np.pi) ** 2) + .7801 + 6.1695 * np.exp(
                -3.4069 * (self.q / 4 / np.pi) ** 2) + 1.1777 * np.exp(
                -9.9868 * (self.q / 4 / np.pi) ** 2) + 2.1435 * np.exp(-80.4922 * (self.q / 4 / np.pi) ** 2),
            'Fe': 6.7127 * np.exp(-.3756 * (self.q / 4 / np.pi) ** 2) + 1.8157 + 12.076 * np.exp(
                -4.9535 * (self.q / 4 / np.pi) ** 2) + 3.2058 * np.exp(
                -16.7354 * (self.q / 4 / np.pi) ** 2) + 2.1868 * np.exp(
                -81.5166 * (self.q / 4 / np.pi) ** 2),
            'Ti': 6.6289 * np.exp(
                -0.6365 * (self.q / 4 / np.pi) ** 2) + 2.2032 + 9.9142 * np.exp(
                -8.2781 * (self.q / 4 / np.pi) ** 2) + 1.0215 * np.exp(
                -39.7076 * (self.q / 4 / np.pi) ** 2) + 2.2186 * np.exp(
                -100.4239 * (self.q / 4 / np.pi) ** 2)}

    def tearDown(self):
        pass

    def test_consistency_of_form_factor(self):
        # values from vitali's glass program
        form_factor_si = calculate_coherent_scattering_factor('Si', self.q)
        self.assertLess(np.abs(np.sum(form_factor_si - self.form_factor_vitali['Si'])), 1e-13)

        form_factor_O = calculate_coherent_scattering_factor('O', self.q)
        self.assertLess(np.abs(np.sum(form_factor_O - self.form_factor_vitali['O'])), 1e-13)

        form_factor_Mg = calculate_coherent_scattering_factor('Mg', self.q)
        self.assertLess(np.abs(np.sum(form_factor_Mg - self.form_factor_vitali['Mg'])), 1e-13)

        form_factor_Fe = calculate_coherent_scattering_factor('Fe', self.q)
        self.assertLess(np.abs(np.sum(form_factor_Fe - self.form_factor_vitali['Fe'])), 1e-12)

        form_factor_Ti = calculate_coherent_scattering_factor('Ti', self.q)
        self.assertLess(np.abs(np.sum(form_factor_Ti - self.form_factor_vitali['Ti'])), 1e-12)

    def test_consistency_of_incoherent_scattering(self):
        incoherent_vitali_si = (14 - (self.form_factor_vitali['Si'] ** 2) / 14) * (
            1 - .5254 * (np.exp(-1.1646 * (self.q / 4 / np.pi)) - np.exp(-14.3259 * (self.q / 4 / np.pi))))
        incoherent_vitali_o = (8 - (self.form_factor_vitali['O'] ** 2) / 8) * (
            1 - .3933 * (np.exp(-1.2843 * (self.q / 4 / np.pi)) - np.exp(-32.682 * (self.q / 4 / np.pi))))
        incoherent_vitali_mg = (12 - (self.form_factor_vitali['Mg'] ** 2) / 12) * (
            1 - 0.5189 * (np.exp(-1.2756 * (self.q / 4 / np.pi)) - np.exp(-15.3134 * (self.q / 4 / np.pi))))
        incoherent_vitali_fe = (26 - (self.form_factor_vitali['Fe'] ** 2) / 26) * (
            1 - 0.6414 * (np.exp(-0.9673 * (self.q / 4 / np.pi)) - np.exp(-10.4405 * (self.q / 4 / np.pi))))

        incoherent_si = calculate_incoherent_scattered_intensity('Si', self.q)
        incoherent_o = calculate_incoherent_scattered_intensity('O', self.q)
        incoherent_mg = calculate_incoherent_scattered_intensity('Mg', self.q)
        incoherent_fe = calculate_incoherent_scattered_intensity('Fe', self.q)

        self.assertLess(np.abs(np.sum(incoherent_si-incoherent_vitali_si)), 1e-12)
        self.assertLess(np.abs(np.sum(incoherent_o-incoherent_vitali_o)), 1e-12)
        self.assertLess(np.abs(np.sum(incoherent_mg-incoherent_vitali_mg)), 1e-12)
        self.assertLess(np.abs(np.sum(incoherent_fe-incoherent_vitali_fe)), 1e-12)







# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest

import numpy as np
import matplotlib.pyplot as plt

from core import spectrum
from gui.model import glassure_model
from gui.model import calc_transforms


class GlassureModelTest(unittest.TestCase):
    def setUp(self):
        self.model = glassure_model()

    def tearDown(self):
        pass

    def limit_spectrum_q(self, spectrum, q_max):
        q, int = spectrum.data
        return spectrum(q[np.where(q < q_max)], int[np.where(q < q_max)])

    def plot_spectrum(self, spectrum):
        x, y = spectrum.data
        plt.plot(x, y)

    def test_calculate_transforms(self):
        data_spectrum = spectrum()
        data_spectrum.load('data/Mg2SiO4_091.xy')

        bkg_spectrum = spectrum()
        bkg_spectrum.load('data/Mg2SiO4_091_bkg.xy')

        self.model.load_data('data/Mg2SiO4_091.xy')
        self.model.load_bkg('data/Mg2SiO4_091_bkg.xy')

        odata1_x, odata1_y = self.model.original_spectrum.data
        odata2_x, odata2_y = data_spectrum.data
        self.assertEqual(np.sum(np.abs(odata1_y - odata2_y)), 0)

        bkg_data1_x, bkg_data1_y = self.model.background_spectrum.data
        bkg_data2_x, bkg_data2_y = bkg_spectrum.data
        self.assertEqual(np.sum(np.abs(bkg_data2_y - bkg_data1_y)), 0)


        q_min = 0
        q_max = 10
        data_spectrum = self.limit_spectrum_q(data_spectrum, q_max)
        bkg_spectrum = self.limit_spectrum_q(bkg_spectrum, q_max)

        density = 1.7
        background_scaling = 0.83133015
        elemental_abundances = {
            'Mg': 2,
            'Si': 1,
            'O': 4,
        }
        r = np.linspace(0, 10, 1000)

        self.model.background_scaling = background_scaling
        self.model.update_parameter(elemental_abundances, density, q_min, q_max, 1.0)
        sq_spectrum, fr_spectrum, gr_spectrum = calc_transforms(data_spectrum, bkg_spectrum,
                                                                background_scaling, elemental_abundances,
                                                                density, r)
        sq_spectrum1_x, sq_spectrum1_y = self.model.sq_spectrum.data
        sq_spectrum2_x, sq_spectrum2_y = sq_spectrum.data


        self.assertEqual(len(sq_spectrum1_x), len(sq_spectrum2_x))

        self.assertEqual(np.sum(np.abs(sq_spectrum1_y - sq_spectrum2_y)), 0)
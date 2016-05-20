# -*- coding: utf8 -*-

import unittest
import os

import numpy as np

from core import Pattern
from core import calculate_sq
from gui.model.glassure_model import GlassureModel

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


class GlassureModelTest(unittest.TestCase):
    def setUp(self):
        self.model = GlassureModel()

    def tearDown(self):
        pass

    def test_calculate_transforms(self):
        data_spectrum = Pattern.from_file(data_path('Mg2SiO4_ambient.xy'))

        bkg_spectrum = Pattern.from_file(data_path('Mg2SiO4_ambient_bkg.xy'))

        self.model.load_data(data_path('Mg2SiO4_ambient.xy'))
        self.model.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))

        odata1_x, odata1_y = self.model.original_pattern.data
        odata2_x, odata2_y = data_spectrum.data
        self.assertEqual(np.sum(np.abs(odata1_y - odata2_y)), 0)

        bkg_data1_x, bkg_data1_y = self.model.background_pattern.data
        bkg_data2_x, bkg_data2_y = bkg_spectrum.data
        self.assertEqual(np.sum(np.abs(bkg_data2_y - bkg_data1_y)), 0)

        q_min = 0
        q_max = 10
        data_spectrum = data_spectrum.limit(0, q_max)
        bkg_spectrum = bkg_spectrum.limit(0, q_max)

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

        sample_spectrum = data_spectrum - background_scaling * bkg_spectrum
        sq_spectrum_core = calculate_sq(sample_spectrum, density, elemental_abundances)


        sq_spectrum1_x, sq_spectrum1_y = self.model.sq_pattern.data
        sq_spectrum2_x, sq_spectrum2_y = sq_spectrum_core.data

        self.assertEqual(len(sq_spectrum1_x), len(sq_spectrum2_x))
        self.assertEqual(np.sum(np.abs(sq_spectrum1_y - sq_spectrum2_y)), 0)

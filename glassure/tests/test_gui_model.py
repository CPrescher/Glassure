# -*- coding: utf8 -*-

import os
import unittest

import numpy as np

from gui.model.glassure_model import GlassureModel

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class GuiModelTest(unittest.TestCase):
    def setUp(self):
        self.model = GlassureModel()
        self.model.load_data(sample_path)
        self.model.load_bkg(bkg_path)

    def test_calculate_spectra(self):
        self.assertIsNone(self.model.sq_spectrum)
        self.assertIsNone(self.model.gr_spectrum)
        self.assertIsNone(self.model.fr_spectrum)

        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        self.assertIsNotNone(self.model.sq_spectrum)
        self.assertIsNotNone(self.model.gr_spectrum)
        self.assertIsNotNone(self.model.fr_spectrum)

    def test_changing_composition(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
        sq1 = self.model.sq_spectrum
        self.model.composition = {'Mg': 1, 'Si': 1.0, 'O': 3.0}
        sq2 = self.model.sq_spectrum
        self.assertFalse(np.allclose(sq1.y, sq2.y))

    def test_changing_q_range(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        sq = self.model.sq_spectrum
        self.assertGreater(np.min(sq.x), self.model.q_min)
        self.assertLess(np.max(sq.x), self.model.q_max)

        self.model.q_min = 1.4
        sq = self.model.sq_spectrum
        self.assertGreater(np.min(sq.x), self.model.q_min)

        self.model.q_max = 9
        sq = self.model.sq_spectrum
        self.assertLess(np.max(sq.x), self.model.q_max)

    def test_changing_density(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        sq1 = self.model.sq_spectrum
        self.model.density = 2.9
        sq2 = self.model.sq_spectrum

        self.assertFalse(np.allclose(sq1.y, sq2.y))

    def test_changing_r_range(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        fr = self.model.fr_spectrum
        self.assertAlmostEqual(np.min(fr.x), self.model.r_min)
        self.assertAlmostEqual(np.max(fr.x), self.model.r_max)

        self.model.r_min = 1.4
        fr = self.model.fr_spectrum
        self.assertAlmostEqual(np.min(fr.x), self.model.r_min)

        self.model.r_max = 9
        fr = self.model.fr_spectrum
        self.assertAlmostEqual(np.max(fr.x), self.model.r_max)

    def test_use_modification_fcn(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        fr1 = self.model.fr_spectrum
        self.model.use_modification_fcn = True
        fr2 = self.model.fr_spectrum
        self.assertFalse(np.allclose(fr1.y, fr2.y))

    def test_optimize_sq(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        sq1 = self.model.sq_spectrum
        self.model.optimize_sq(5, use_modification_fcn=False)
        sq2 = self.model.sq_spectrum
        self.assertFalse(np.allclose(sq1.y, sq2.y))

# -*- coding: utf8 -*-

import os

import numpy as np

from glassure.core import Pattern
from glassure.core import calculate_sq
from glassure.gui.model.glassure import GlassureModel
from .utility import data_path, QtTest



class GlassureModelTest(QtTest):
    def setUp(self):
        self.model = GlassureModel()
        self.model.load_data(data_path('Mg2SiO4_ambient.xy'))
        self.model.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))

    def tearDown(self):
        pass

    def test_calculate_transforms(self):
        data_pattern = Pattern.from_file(data_path('Mg2SiO4_ambient.xy'))
        bkg_pattern = Pattern.from_file(data_path('Mg2SiO4_ambient_bkg.xy'))

        odata1_x, odata1_y = self.model.original_pattern.data
        odata2_x, odata2_y = data_pattern.data
        self.assertEqual(np.sum(np.abs(odata1_y - odata2_y)), 0)

        bkg_data1_x, bkg_data1_y = self.model.background_pattern.data
        bkg_data2_x, bkg_data2_y = bkg_pattern.data
        self.assertEqual(np.sum(np.abs(bkg_data2_y - bkg_data1_y)), 0)

        q_min = 0
        q_max = 10
        data_pattern = data_pattern.limit(0, q_max)
        bkg_pattern = bkg_pattern.limit(0, q_max)

        density = 1.7
        background_scaling = 0.83133015
        elemental_abundances = {
            'Mg': 2,
            'Si': 1,
            'O': 4,
        }
        r = np.linspace(0, 10, 1000)

        self.model.background_scaling = background_scaling
        self.model.update_parameter(elemental_abundances, density, q_min, q_max, 0, 10, False,
                                    None, {}, False, 1.5, 5, 1)

        sample_pattern = data_pattern - background_scaling * bkg_pattern
        sq_pattern_core = calculate_sq(sample_pattern, density, elemental_abundances)

        sq_pattern1_x, sq_pattern1_y = self.model.sq_pattern.data
        sq_pattern2_x, sq_pattern2_y = sq_pattern_core.data

        self.assertEqual(len(sq_pattern1_x), len(sq_pattern2_x))
        self.assertEqual(np.sum(np.abs(sq_pattern1_y - sq_pattern2_y)), 0)

    def test_calculate_spectra(self):
        self.assertIsNone(self.model.sq_pattern)
        self.assertIsNone(self.model.gr_pattern)
        self.assertIsNone(self.model.fr_pattern)

        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        self.assertIsNotNone(self.model.sq_pattern)
        self.assertIsNotNone(self.model.gr_pattern)
        self.assertIsNotNone(self.model.fr_pattern)

    def test_changing_composition(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
        sq1 = self.model.sq_pattern
        self.model.composition = {'Mg': 1, 'Si': 1.0, 'O': 3.0}
        sq2 = self.model.sq_pattern
        self.assertFalse(np.allclose(sq1.y, sq2.y))

    def test_changing_q_range(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
        self.model.extrapolation_method = None

        sq = self.model.sq_pattern
        self.assertGreater(np.min(sq.x), self.model.q_min)
        self.assertLess(np.max(sq.x), self.model.q_max)

        self.model.q_min = 1.4
        sq = self.model.sq_pattern
        self.assertGreater(np.min(sq.x), self.model.q_min)

        self.model.q_max = 9
        sq = self.model.sq_pattern
        self.assertLess(np.max(sq.x), self.model.q_max)

    def test_changing_density(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        sq1 = self.model.sq_pattern
        self.model.density = 2.9
        sq2 = self.model.sq_pattern

        self.assertFalse(np.allclose(sq1.y, sq2.y))

    def test_changing_r_range(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        fr = self.model.fr_pattern
        self.assertAlmostEqual(np.min(fr.x), self.model.r_min)
        self.assertAlmostEqual(np.max(fr.x), self.model.r_max)

        self.model.r_min = 1.4
        fr = self.model.fr_pattern
        self.assertAlmostEqual(np.min(fr.x), self.model.r_min)

        self.model.r_max = 9
        fr = self.model.fr_pattern
        self.assertAlmostEqual(np.max(fr.x), self.model.r_max)

    def test_use_modification_fcn(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        fr1 = self.model.fr_pattern
        self.model.use_modification_fcn = True
        fr2 = self.model.fr_pattern
        self.assertFalse(np.allclose(fr1.y, fr2.y))

    def test_optimize_sq(self):
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

        sq1 = self.model.sq_pattern
        self.model.optimize = True
        sq2 = self.model.sq_pattern
        self.assertFalse(np.allclose(sq1.y, sq2.y))

    def test_adding_a_configuration(self):
        # Adding a configuration and then change one parameter to see if new configuration behaves independently
        self.model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
        sq1 = self.model.sq_pattern

        self.assertLess(sq1.x[-1], 10)

        self.model.add_configuration()
        sq2 = self.model.sq_pattern

        self.assertLess(sq2.x[-1], 10)

        self.model.q_max = 12
        sq2 = self.model.sq_pattern

        self.assertLess(sq1.x[-1], 10)
        self.assertGreater(sq2.x[-1], 10)

    def test_selecting_a_configuration(self):
        self.model.add_configuration()
        self.model.q_max = 12

        self.model.add_configuration()
        self.model.q_max = 14

        self.model.select_configuration(0)
        self.assertEqual(self.model.q_max, 10)

        self.model.select_configuration(1)
        self.assertEqual(self.model.q_max, 12)

        self.model.select_configuration(2)
        self.assertEqual(self.model.q_max, 14)

    def test_removing_configuration_with_only_one_configuration(self):
        # should not remove the last configuration!
        self.model.remove_configuration()
        self.assertEqual(len(self.model.configurations), 1)

    def test_remove_last_configuration(self):
        self.model.add_configuration()
        self.model.q_max = 12
        self.model.add_configuration()
        self.model.q_max = 14

        self.assertEqual(self.model.q_max, 14)
        self.model.remove_configuration()
        self.assertEqual(self.model.q_max, 12)

        self.model.select_configuration(1)
        self.model.remove_configuration()
        self.assertEqual(self.model.q_max, 10)

    def test_remove_center_configuration(self):
        self.model.add_configuration()
        self.model.q_max = 12
        self.model.add_configuration()
        self.model.q_max = 14

        self.model.select_configuration(1)
        self.assertEqual(self.model.q_max, 12)
        self.model.remove_configuration()
        self.assertEqual(self.model.q_max, 14)

    def test_use_transfer_function(self):
        sample_path = data_path('glass_rod_SS.xy')
        std_path = data_path('glass_rod_WOS.xy')

        self.model.load_data(sample_path)
        self.model.load_bkg(sample_path)
        self.model.background_scaling = 0
        self.model.q_min = 0
        self.model.q_max = 14
        self.model.composition = {'Si': 1.0, 'O': 2.0}

        sq_pattern_before = self.model.sq_pattern

        self.model.load_transfer_sample_pattern(sample_path)
        self.model.load_transfer_std_pattern(std_path)

        self.model.use_transfer_function = True
        test_y = self.model.original_pattern.limit(0, 14).y * self.model.transfer_function(
            self.model.original_pattern.limit(0, 14).x)
        self.assertAlmostEqual(np.std(self.model.transfer_std_pattern.limit(0, 14).y / test_y), 0, delta=0.2)

        sq_pattern_with_transfer = self.model.sq_pattern

        self.assertFalse(np.array_equal(sq_pattern_before.y, sq_pattern_with_transfer.y))

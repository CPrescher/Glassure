# -*- coding: utf8 -*-

import os
import unittest
from mock import MagicMock

import numpy as np

from glassure.core import Pattern
from glassure.gui.controller.glassure import GlassureController
from glassure.gui.qt import QtGui
from glassure.tests.gui_tests.utility import click_button, click_checkbox, array_almost_equal

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


class TransferWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication.instance()
        if cls.app is None:
            cls.app = QtGui.QApplication([])

    def setUp(self):
        self.controller = GlassureController()
        self.widget = self.controller.main_widget
        self.transfer_widget = self.widget.transfer_widget
        self.model = self.controller.model

        self.model.q_min = 1.5
        self.model.q_max = 10

        self.widget.left_control_widget.composition_widget.add_element('O', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)

        self.controller.load_data(data_path('glass_rod_SS.xy'))
        self.controller.load_bkg(data_path('glass_rod_SS.xy'))
        self.model.background_scaling = 0

    def test_activate_transfer_correction(self):
        click_checkbox(self.transfer_widget.activate_cb)
        self.assertTrue(self.model.use_transfer_function)

    def test_loading_sample_data(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)
        self.assertIsNotNone(self.model.transfer_sample_pattern)
        self.assertEqual(str(self.transfer_widget.sample_filename_lbl.text()), 'glass_rod_SS.xy')

    def test_loading_sample_bkg_data(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_bkg_btn)
        self.assertIsNotNone(self.model.transfer_sample_bkg_pattern)
        self.assertEqual(str(self.transfer_widget.sample_bkg_filename_lbl.text()), 'glass_rod_SS.xy')

    def test_loading_std_data(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        self.assertIsNotNone(self.model.transfer_std_pattern)
        self.assertEqual(str(self.transfer_widget.std_filename_lbl.text()), 'glass_rod_WOS.xy')

    def test_loading_std_bkg_data(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_bkg_btn)
        self.assertIsNotNone(self.model.transfer_std_bkg_pattern)
        self.assertEqual(str(self.transfer_widget.std_bkg_filename_lbl.text()), 'glass_rod_WOS.xy')

    def test_transfer_function_exists(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        self.assertIsNone(self.model.transfer_function)
        click_checkbox(self.transfer_widget.activate_cb)
        self.assertIsNotNone(self.model.transfer_function)

    def test_transfer_function_modifies_pattern(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        _, y_before = self.model.sq_pattern.data
        click_checkbox(self.transfer_widget.activate_cb)
        _, y_after = self.model.sq_pattern.data

        self.assertFalse(np.array_equal(y_before, y_after))

    def test_change_sample_bkg_scaling(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        sample_bkg_pattern = Pattern(self.model.transfer_sample_pattern.x,
                                     np.ones(self.model.transfer_sample_pattern.y.shape))

        self.model.transfer_sample_bkg_pattern = sample_bkg_pattern
        self.model.transfer_sample_bkg_scaling = 0
        click_checkbox(self.transfer_widget.activate_cb)

        _, y_before = self.model.sq_pattern.data
        self.transfer_widget.sample_bkg_scaling_sb.setValue(50)
        self.assertEqual(self.model.transfer_sample_bkg_scaling, 50)
        _, y_after = self.model.sq_pattern.data

        self.assertFalse(np.array_equal(y_after, y_before))

    def test_change_std_bkg_scaling(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        std_bkg_pattern = Pattern(self.model.transfer_std_pattern.x,
                                  np.ones(self.model.transfer_std_pattern.y.shape))

        self.model.transfer_std_bkg_pattern = std_bkg_pattern
        self.model.transfer_std_bkg_scaling = 0
        click_checkbox(self.transfer_widget.activate_cb)

        _, y_before = self.model.sq_pattern.data
        self.transfer_widget.std_bkg_scaling_sb.setValue(50)
        self.assertEqual(self.model.transfer_std_bkg_scaling, 50)
        _, y_after = self.model.sq_pattern.data

        self.assertFalse(np.array_equal(y_after, y_before))

    def test_change_smoothing(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        click_checkbox(self.transfer_widget.activate_cb)

        _, y_before = self.model.sq_pattern.data
        self.transfer_widget.smooth_sb.setValue(10)
        self.assertEqual(self.model.transfer_function_smoothing, 10)
        _, y_after = self.model.sq_pattern.data

        self.assertFalse(np.array_equal(y_after, y_before))

    def test_transfer_function_gets_deactivated(self):
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_WOS.xy'))
        click_button(self.transfer_widget.load_std_btn)
        QtGui.QFileDialog.getOpenFileName = MagicMock(return_value=data_path('glass_rod_SS.xy'))
        click_button(self.transfer_widget.load_sample_btn)

        click_checkbox(self.transfer_widget.activate_cb)

        _, y_before = self.model.sq_pattern.data
        click_checkbox(self.transfer_widget.activate_cb)
        _, y_after = self.model.sq_pattern.data

        self.assertFalse(np.array_equal(y_after, y_before))

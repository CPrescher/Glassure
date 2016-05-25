# -*- coding: utf8 -*-

import unittest
import os

import numpy as np
from gui.qt import QtGui, QtCore, QTest

from gui.controller.gui_controller import GlassureController

from tests.utility import set_widget_text, click_checkbox, click_button

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')


class ConfigurationControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.exit()
        cls.app.quit()
        cls.app.deleteLater()
        del cls.app

    def setUp(self):
        self.main_controller = GlassureController()
        self.main_widget = self.main_controller.main_widget
        self.configuration_widget = self.main_widget.configuration_widget
        self.configuration_controller = self.main_controller.configuration_controller
        self.model = self.main_controller.model

    def test_data_filename_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.model.original_pattern.name = 'lala'

        self.configuration_controller.update_configurations_tw()
        self.assertEqual(str(self.main_widget.data_filename_lbl.text()), 'lala')

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(str(self.main_widget.data_filename_lbl.text()), '')

    def test_bkg_filename_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.model.current_configuration.background_pattern.name = 'lala'

        self.configuration_controller.update_configurations_tw()
        self.assertEqual(str(self.main_widget.bkg_filename_lbl.text()), 'lala')

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(str(self.main_widget.bkg_filename_lbl.text()), '')

    def test_bkg_scaling_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.main_widget.bkg_scaling_sb.setValue(0.3)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(self.main_widget.bkg_scaling_sb.value(), 1)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.main_widget.bkg_scaling_sb.value(), .3)

    def test_smooth_factor_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.main_widget.smooth_sb.setValue(4)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(self.main_widget.smooth_sb.value(), 0)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.main_widget.smooth_sb.value(), 4)

    def test_composition_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.main_widget.add_element_btn)
        click_button(self.main_widget.add_element_btn)
        element_cb = self.main_widget.composition_tw.cellWidget(1, 0)
        element_cb.setCurrentIndex(2)

        self.assertEqual(self.main_widget.composition_tw.rowCount(), 2)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(self.main_widget.composition_tw.rowCount(), 0)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.main_widget.composition_tw.rowCount(), 2)

    def txt_widget_update_test(self, test_widget, value):
        click_button(self.configuration_widget.freeze_btn)
        prev_value = float(str(test_widget.text()))
        set_widget_text(test_widget, value)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(float(str(test_widget.text())), prev_value)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(float(str(test_widget.text())), value)

    def test_density_is_updated(self):
        self.txt_widget_update_test(self.main_widget.density_txt, 2.9)

    def test_q_min_is_updated(self):
        self.txt_widget_update_test(self.main_widget.q_min_txt, 2)

    def test_q_max_is_updated(self):
        self.txt_widget_update_test(self.main_widget.q_max_txt, 9)

    def test_r_min_is_updated(self):
        self.txt_widget_update_test(self.main_widget.r_min_txt, 0.1)

    def test_r_max_is_updated(self):
        self.txt_widget_update_test(self.main_widget.r_max_txt, 9.5)

    def test_use_modification_function_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        click_checkbox(self.main_widget.use_modification_cb)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertFalse(self.main_widget.use_modification_cb.isChecked())

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertTrue(self.main_widget.use_modification_cb.isChecked())

    def test_configuration_method_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        click_checkbox(self.main_widget.left_control_widget.extrapolation_widget.linear_extrapolation_rb)
        click_button(self.configuration_widget.freeze_btn)
        click_checkbox(self.main_widget.activate_extrapolation_cb)  # deactivate

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertTrue(self.main_widget.activate_extrapolation_cb.isChecked())
        self.assertTrue(self.main_widget.left_control_widget.extrapolation_widget.step_extrapolation_rb.isChecked())

    def test_configuration_parameters_are_updated(self):
        click_checkbox(self.main_widget.left_control_widget.extrapolation_widget.poly_extrapolation_rb)
        click_button(self.configuration_widget.freeze_btn)

        set_widget_text(self.main_widget.left_control_widget.extrapolation_widget.q_max_txt, 1.4)
        click_checkbox(self.main_widget.left_control_widget.extrapolation_widget.replace_cb)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(float(str(self.main_widget.left_control_widget.extrapolation_widget.q_max_txt.text())), 2)
        self.assertFalse(self.main_widget.left_control_widget.extrapolation_widget.replace_cb.isChecked())

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(float(str(self.main_widget.left_control_widget.extrapolation_widget.q_max_txt.text())), 1.4)
        self.assertTrue(self.main_widget.left_control_widget.extrapolation_widget.replace_cb.isChecked())

    def test_r_cutoff_is_updated(self):
        self.txt_widget_update_test(self.main_widget.optimize_r_cutoff_txt, 1.8)



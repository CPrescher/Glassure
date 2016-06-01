# -*- coding: utf8 -*-

import os
import unittest

from mock import patch

from gui.controller.glassure import GlassureController
from gui.qt import QtGui
from tests.gui_tests.utility import set_widget_text, click_checkbox, click_button

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


class Widget_ConfigurationControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication.instance()
        if cls.app is None:
            cls.app = QtGui.QApplication([])

    def setUp(self):
        self.main_controller = GlassureController()
        self.main_widget = self.main_controller.main_widget
        self.configuration_widget = self.main_widget.configuration_widget
        self.configuration_controller = self.main_controller.configuration_controller
        self.model = self.main_controller.model

    def test_data_filename_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.model.original_pattern.name = 'lala'

        self.configuration_controller.update_widget_controls()
        self.assertEqual(str(self.main_widget.data_filename_lbl.text()), 'lala')

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(str(self.main_widget.data_filename_lbl.text()), '')

    def test_bkg_filename_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.model.current_configuration.background_pattern.name = 'lala'

        self.configuration_controller.update_widget_controls()
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

    def test_optimization_activate_is_updated(self):
        activate_cb = self.main_widget.optimize_activate_cb
        click_button(self.configuration_widget.freeze_btn)
        click_checkbox(activate_cb)
        click_button(self.configuration_widget.freeze_btn)

        self.assertTrue(activate_cb.isChecked())

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertFalse(activate_cb.isChecked())

    def test_r_cutoff_is_updated(self):
        self.txt_widget_update_test(self.main_widget.optimize_r_cutoff_txt, 5)

    def test_optimization_iterations_is_updated(self):
        self.txt_widget_update_test(self.main_widget.optimize_iterations_txt, 3)

    def test_optimization_attenuation_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        self.main_widget.optimize_attenuation_sb.setValue(4)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(self.main_widget.optimize_attenuation_sb.value(), 1)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.main_widget.optimize_attenuation_sb.value(), 4)

    def test_soller_active_is_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        click_checkbox(self.main_widget.soller_active_cb)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertFalse(self.main_widget.soller_active_cb.isChecked())

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertTrue(self.main_widget.soller_active_cb.isChecked())

    def test_soller_parameters_are_updated(self):
        click_button(self.configuration_widget.freeze_btn)
        set_widget_text(self.main_widget.right_control_widget.soller_widget.wavelength_txt.value_txt, 0.3344)

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(self.main_widget.right_control_widget.soller_widget.wavelength_txt.get_value(), 0.31)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.main_widget.right_control_widget.soller_widget.wavelength_txt.get_value(), 0.3344)

    def test_soller_parameters_stress_test(self):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)

        soller_parameters1 = self.main_widget.soller_widget.get_parameters()

        soller_parameters2 = {'sample_thickness': 2.0,  # in mm
                              'wavelength': 0.3,  # in Angstrom
                              'inner_radius': 61,  # in mm
                              'outer_radius': 220,  # in mm
                              'inner_width': 0.01,  # in mm
                              'outer_width': 0.3,  # in mm
                              'inner_length': 2,  # in mm
                              'outer_length': 4}  # in mm

        soller_parameters3 = {'sample_thickness': 1.5,  # in mm
                              'wavelength': 0.1,  # in Angstrom
                              'inner_radius': 34,  # in mm
                              'outer_radius': 212,  # in mm
                              'inner_width': 0.123,  # in mm
                              'outer_width': 0.32,  # in mm
                              'inner_length': 4,  # in mm
                              'outer_length': 5}  # in mm

        self.configuration_widget.configuration_tw.selectRow(1)
        self.model.soller_parameters = soller_parameters2
        self.configuration_widget.configuration_tw.selectRow(2)
        self.model.soller_parameters = soller_parameters3

        self.configuration_widget.configuration_tw.selectRow(0)
        self.assertEqual(soller_parameters1, self.main_widget.soller_widget.get_parameters())
        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(soller_parameters2, self.main_widget.soller_widget.get_parameters())
        self.configuration_widget.configuration_tw.selectRow(2)
        self.assertEqual(soller_parameters3, self.main_widget.soller_widget.get_parameters())


class Pattern_ConfigurationControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication.instance()
        if cls.app is None:
            cls.app = QtGui.QApplication([])

    def setUp(self):
        self.main_controller = GlassureController()
        self.main_widget = self.main_controller.main_widget
        self.configuration_widget = self.main_widget.configuration_widget
        self.configuration_controller = self.main_controller.configuration_controller
        self.model = self.main_controller.model

    def test_new_plots_are_created(self):
        click_button(self.configuration_widget.freeze_btn)
        self.assertEqual(len(self.main_widget.spectrum_widget.gr_items), 2)

    def test_plot_items_are_removed(self):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.remove_btn)
        self.assertEqual(len(self.main_widget.spectrum_widget.gr_items), 2)

    def test_plot_items_show_different_data(self):
        click_button(self.main_widget.add_element_btn)
        click_button(self.configuration_widget.freeze_btn)
        set_widget_text(self.main_widget.q_max_txt, 12)

        x1, y1 = self.main_widget.spectrum_widget.sq_items[0].getData()
        x2, y2 = self.main_widget.spectrum_widget.sq_items[1].getData()

        self.assertNotAlmostEqual(x1[-1], x2[-1])

    def test_correct_configuration_selected_after_remove(self):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)

        self.configuration_widget.configuration_tw.selectRow(1)
        self.assertEqual(self.model.configuration_ind, 1)

        click_button(self.configuration_widget.remove_btn)
        self.assertEqual(self.model.configuration_ind, 1)
        self.assertEqual(self.configuration_widget.configuration_tw.selectedIndexes()[0].row(), 1)

    def test_changing_configuration_visibility(self):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)

        click_checkbox(self.configuration_widget.configuration_show_cbs[1])

        self.assertFalse(self.main_widget.spectrum_widget.gr_items[1] in
                         self.main_widget.spectrum_widget.gr_plot.items)
        self.assertFalse(self.main_widget.spectrum_widget.sq_items[1] in
                         self.main_widget.spectrum_widget.sq_plot.items)

        click_checkbox(self.configuration_widget.configuration_show_cbs[1])

        self.assertTrue(self.main_widget.spectrum_widget.gr_items[1] in
                        self.main_widget.spectrum_widget.gr_plot.items)
        self.assertTrue(self.main_widget.spectrum_widget.sq_items[1] in
                        self.main_widget.spectrum_widget.sq_plot.items)

    @patch('PyQt4.QtGui.QColorDialog.getColor')
    def test_changing_configuration_color(self, getColor):
        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)

        # changing a non-active configuration will change its color immediately in the pattern widget:
        new_color = QtGui.QColor(233, 1, 3)
        getColor.return_value = new_color
        click_button(self.configuration_widget.configuration_color_btns[1])
        self.assertEqual(self.main_widget.spectrum_widget.sq_items[1].opts['pen'].color().rgb(), new_color.rgb())

        # changing the active color, will have no effect on current color
        new_color = QtGui.QColor(233, 1, 255)
        getColor.return_value = new_color
        click_button(self.configuration_widget.configuration_color_btns[2])
        self.assertNotEqual(self.main_widget.spectrum_widget.sq_items[2].opts['pen'].color().rgb(), new_color.rgb())

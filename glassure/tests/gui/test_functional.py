# -*- coding: utf8 -*-

import unittest
import os

import numpy as np
from gui.qt import QtGui

from gui.controller.glassure import GlassureController

from tests.utility import set_widget_text, click_checkbox, click_button

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


class GlassureFunctionalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication.instance()
        if cls.app is None:
            cls.app = QtGui.QApplication([])

    def setUp(self):
        self.main_controller = GlassureController()
        self.main_widget = self.main_controller.main_widget
        self.model = self.main_controller.model

    def test_normal_workflow(self):
        # Edd opens the program and wants to load his data and background file:

        self.main_controller.load_data(os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy'))
        self.main_controller.load_bkg(os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy'))

        # he gives the composition of the sample and the normalization procedure is automatically done and he sees
        # a computed g(r) and s(q)

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()

        self.main_widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.main_widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.main_widget.left_control_widget.composition_widget.add_element('O', 4)

        self.assertEqual(self.model.composition, {'Mg': 2, 'Si': 1, 'O': 4})

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # Now he wants to enter the correct density value:
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()
        set_widget_text(self.main_widget.density_txt, 2.9)
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # Then he he adjusts the scale of the background data and it automatically adjusts sq and gr
        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()

        self.main_widget.bkg_scaling_sb.setValue(0.5)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # now he adjusts the smoothing and sees the things change in respect to
        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()

        self.main_widget.smooth_sb.setValue(3)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # now he wants to see how the data looks when choosing a larger Q-range
        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()

        set_widget_text(self.main_widget.q_max_txt, 12)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # he thinks there are still strong oscillations at the lower r-region, and wants to see what the Loch
        # modification function will do

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        prev_gr_data = self.main_widget.spectrum_widget.gr_items[0].getData()

        click_checkbox(self.main_widget.use_modification_cb)

        self.assertTrue(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.gr_items[0].getData()))

        # the data unfortunately is not measured up to a Q of 0 A^-1, however the missing data below 1 A^-1 is already
        # extrapolated with a step function, he thinks the polynomial option might be a better choice, selects it and
        # sees the change:

        self.assertLess(self.main_widget.spectrum_widget.sq_items[0].getData()[0][0], 0.5)

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        click_checkbox(self.main_widget.left_control_widget.extrapolation_widget.poly_extrapolation_rb)
        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))

        # changing the q_max value, gives an even better result for the polynomial extrapolation

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        set_widget_text(self.main_widget.extrapolation_q_max_txt, 1.5)
        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))

        # looks good already! However, the oscillations below 1 Angstrom bother him still a lot, so he wants to
        # optimize this by using the Eggert et al. (2002) method:

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        click_checkbox(self.main_widget.optimize_activate_cb)
        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))

        # However he realizes that the default cutoff might too low for this kind of data. and gives a larger number,
        # and optimizes again:

        prev_sq_data = self.main_widget.spectrum_widget.sq_items[0].getData()
        set_widget_text(self.main_widget.optimize_r_cutoff_txt, 1.2)
        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_items[0].getData()))

    def test_working_with_configurations(self):
        # Edd starts to mak some analysis

        self.main_controller.load_data(os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy'))
        self.main_controller.load_bkg(os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy'))

        self.main_widget.left_control_widget.composition_widget.add_element('Si', 1)

        # He likes the default parameters, but wants to test it against another density, therefore he saves the current
        # state

        click_button(self.main_widget.freeze_configuration_btn)

        # and magically sees that there are now is a field in the configuration table and extra other lines in the plot
        # widgets

        self.assertEqual(self.main_widget.configuration_tw.rowCount(), 2)

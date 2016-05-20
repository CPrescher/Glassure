# -*- coding: utf8 -*-

import unittest
import os

import numpy as np
from gui.qt import QtGui, QtCore, QTest

from gui.controller.gui_controller import GlassureController

from tests.utility import set_widget_text, click_checkbox

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')


class GlassureFunctionalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()
        cls.app.deleteLater()
        del cls.app

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

        prev_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_widget.spectrum_widget.pdf_item.getData()

        self.main_widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.main_widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.main_widget.left_control_widget.composition_widget.add_element('O', 4)

        self.assertEqual(self.model.composition, {'Mg': 2, 'Si': 1, 'O': 4})

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.pdf_item.getData()))

        # Then he he adjusts the scale of the background data and it automatically adjusts sq and gr
        prev_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_widget.spectrum_widget.pdf_item.getData()

        self.main_widget.bkg_scaling_sb.setValue(0.5)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.pdf_item.getData()))

        # now he adjusts the smoothing and sees the things change in respect to
        prev_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_widget.spectrum_widget.pdf_item.getData()

        self.main_widget.smooth_sb.setValue(3)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.pdf_item.getData()))

        # now he wants to see how the data looks when choosing a larger Q-range
        prev_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_widget.spectrum_widget.pdf_item.getData()

        set_widget_text(self.main_widget.q_max_txt, 12)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.pdf_item.getData()))

        # he thinks there are still strong oscillations at the lower r-region, and wants to see what the Loch
        # modification function will do

        prev_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_widget.spectrum_widget.pdf_item.getData()

        click_checkbox(self.main_widget.use_modification_cb)

        self.assertTrue(np.array_equal(prev_sq_data, self.main_widget.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_widget.spectrum_widget.pdf_item.getData()))

        # the data unfortunately is not measured up to a Q of 0 A^-1, however the missing data below 1 A^-1 might have
        # an effect on the optimization procedure later, therefor he wants to activate interpolation to zero

        click_checkbox(self.main_widget.activate_interpolation_cb)

        # new_sq_data = self.main_widget.spectrum_widget.sq_item.getData()
        # self.assertLess(new_sq_data[0][0], 0.5)

        # self.assertLess(self.)

        # self.fail("finish this test!")

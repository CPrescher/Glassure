# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import os

import numpy as np
from gui.qt import QtGui

from gui.controller.gui_controller import MainController

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')

class GlassureFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.app = QtGui.QApplication([])
        self.main_controller = MainController()
        self.main_view = self.main_controller.main_widget
        self.model = self.main_controller.model

    def tearDown(self):
        del self.app

    def test_normal_workflow(self):
        #Edd opens the program and wants to load his data and background file:

        self.main_controller.load_data(os.path.join(unittest_data_path, 'Mg2SiO4_091.xy'))
        self.main_controller.load_bkg(os.path.join(unittest_data_path, 'Mg2SiO4_091_bkg.xy'))

        # he gives the composition of the sample and the normalization procedure is automatically done and he sees
        # a computed g(r) and s(q)

        prev_sq_data = self.main_view.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_view.spectrum_widget.pdf_item.getData()

        self.main_view.left_control_widget.composition_widget.add_element('Mg', 2)
        self.main_view.left_control_widget.composition_widget.add_element('Si', 1)
        self.main_view.left_control_widget.composition_widget.add_element('O', 4)

        self.assertEqual(self.model.composition, {'Mg': 2, 'Si': 1, 'O': 4})

        self.assertFalse(np.array_equal(prev_sq_data, self.main_view.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_view.spectrum_widget.pdf_item.getData()))

        # Then he he adjusts the scale of the background data and it automatically adjusts sq and gr
        prev_sq_data = self.main_view.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_view.spectrum_widget.pdf_item.getData()

        self.model.background_scaling = .5

        self.assertFalse(np.array_equal(prev_sq_data, self.main_view.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_view.spectrum_widget.pdf_item.getData()))

        # now he adjusts the smoothing and sees the things change in respect to
        prev_sq_data = self.main_view.spectrum_widget.sq_item.getData()
        prev_gr_data = self.main_view.spectrum_widget.pdf_item.getData()

        self.model.set_smooth(3)

        self.assertFalse(np.array_equal(prev_sq_data, self.main_view.spectrum_widget.sq_item.getData()))
        self.assertFalse(np.array_equal(prev_gr_data, self.main_view.spectrum_widget.pdf_item.getData()))


        self.fail("finish this test!")

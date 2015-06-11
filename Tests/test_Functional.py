# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import sys
import numpy as np
import os
from PyQt4.QtTest import QTest
from PyQt4 import QtCore, QtGui

from Controller.MainController import MainController

unittest_data_path = os.path.join(os.path.dirname(__file__), 'TestData')

class GlassureFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.main_controller = MainController()
        self.main_view = self.main_controller.main_widget
        self.model = self.main_controller.model

    def tearDown(self):
        del self.app

    def test_normal_workflow(self):
        #Edd opens the program and wants to load his data and background file:

        self.main_controller.load_data(os.path.join(unittest_data_path, 'Mg2SiO4_091.xy'))

        _, prev_spectrum_y = self.model.original_spectrum.data
        self.main_controller.load_bkg(os.path.join(unittest_data_path, 'Mg2SiO4_091_bkg.xy'))

        _, new_spectrum_y = self.model.original_spectrum.data
        self.assertFalse(np.array_equal(prev_spectrum_y, new_spectrum_y))
        prev_spectrum_y = new_spectrum_y

        QTest.keyClicks(self.main_view.bkg_scale_sb, '0.5')
        _, new_spectrum_y = self.model.original_spectrum.data
        self.assertFalse(np.array_equal(prev_spectrum_y, new_spectrum_y))

        #then he adjusts the scale and offset of the background data


        # then he gives the composition of the sample and the normalization procedure is automatically done
        self.fail("finish this test!")

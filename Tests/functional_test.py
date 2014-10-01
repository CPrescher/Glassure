# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import sys
import os
from PyQt4.QtTest import QTest
from PyQt4 import QtCore, QtGui

from Controller.MainController import MainController

class GlassureFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.main_controller = MainController()
        self.main_view = self.main_controller.view

    def tearDown(self):
        del self.app

    def test_normal_workflow(self):
        #Edd opens the program and wants to load his data and background file:

        self.main_controller.load_data('TestData/Mg2SiO4_120.xy')
        self.main_controller.load_bkg('TestData/Mg2SiO4_120_bkg.xy')

        #then he adjusts the scale and offset of the background data


        # then he gives the composition of the sample and the normalization procedure is automatically done
        self.fail("finish this test!")

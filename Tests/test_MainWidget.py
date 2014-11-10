# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import sys
from PyQt4 import QtCore, QtGui
from PyQt4.QtTest import QTest

from Controller.MainController import MainController
from Views.MainWidget import MainWidget

class MainWidgetTest(unittest.TestCase):
    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.main_controller = MainController()
        self.main_view = self.main_controller.main_widget

    def tearDown(self):
        del self.app

    def test_adding_elements(self):
        QTest.mouseClick(self.main_view.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.main_view.composition_tw.rowCount(), 1)
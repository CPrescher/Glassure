# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import unittest
import sys

import numpy as np
from PyQt4 import QtCore, QtGui
from PyQt4.QtTest import QTest

from gui.controller import MainController


class InterpolationWidgetTest(unittest.TestCase):
    def setUp(self):
        self.app = QtGui.QApplication(sys.argv)
        self.controller = MainController()
        self.controller.load_data('data/Mg2SiO4_ambient.xy')
        self.controller.load_bkg('data/Mg2SiO4_ambient_bkg.xy')
        self.data = self.controller.model
        self.widget = self.controller.main_widget
        self.interpolation_widget = self.widget.left_control_widget.interpolation_widget
        self.widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.widget.left_control_widget.composition_widget.add_element('O', 4)

    def tearDown(self):
        del self.app

    def test_activating_interpolation(self):
        #without interpolation S(Q) should have no values below
        q, sq = self.data.sq_spectrum.data
        self.assertGreater(q[0], 1)

        #when turning interpolation on, it should automatically interpolate sq of to zero and recalculate everything

        QTest.mouseClick(self.interpolation_widget.activate_cb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2,self.interpolation_widget.activate_cb.height()/2))
        QtGui.QApplication.processEvents()
        self.assertTrue(self.interpolation_widget.activate_cb.isChecked())

        q, sq = self.data.sq_spectrum.data
        self.assertLess(q[0], 1)

        #using a linear interpolation to zero the sum between 0 and 0.5 should be always different from 0:
        self.assertNotAlmostEqual(np.sum(sq[np.where(q<0.4)]), 0)

        #now switching on spline interpolation and test for 0 values below the cutoff
        QTest.mouseClick(self.interpolation_widget.spline_interpolation_rb, QtCore.Qt.LeftButton,
                          pos=QtCore.QPoint(2,self.interpolation_widget.spline_interpolation_rb.height()/2))
        QtGui.QApplication.processEvents()
        self.assertTrue(self.interpolation_widget.spline_interpolation_rb.isChecked())

        q, sq = self.data.sq_spectrum.data
        self.assertAlmostEqual(np.sum(sq[np.where(q<0.5)]), 0)

    def test_interpolation_parameters(self):
        QTest.mouseClick(self.interpolation_widget.activate_cb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2,self.interpolation_widget.activate_cb.height()/2))
        QTest.mouseClick(self.interpolation_widget.spline_interpolation_rb, QtCore.Qt.LeftButton,
                          pos=QtCore.QPoint(2,self.interpolation_widget.spline_interpolation_rb.height()/2))
        QtGui.QApplication.processEvents()

        self.interpolation_widget.spline_interpolation_cutoff_txt.setText('')
        QTest.keyClicks(self.interpolation_widget.spline_interpolation_cutoff_txt, '0.7')
        QTest.keyClick(self.interpolation_widget.spline_interpolation_cutoff_txt, QtCore.Qt.Key_Enter)
        QtGui.QApplication.processEvents()
        q, sq = self.data.sq_spectrum.data
        self.assertAlmostEqual(np.sum(sq[np.where(q<0.6)]),0)












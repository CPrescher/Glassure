# -*- coding: utf8 -*-

import unittest
import os

import numpy as np

from gui.qt import QtCore, QtGui, QTest
from gui.controller.gui_controller import GlassureController

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


class ExtrapolationWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()
        cls.app.deleteLater()
        del cls.app

    def setUp(self):
        self.controller = GlassureController()
        self.controller.load_data(data_path('Mg2SiO4_ambient.xy'))
        self.controller.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))
        self.data = self.controller.model
        self.widget = self.controller.main_widget
        self.extrapolation_widget = self.widget.left_control_widget.extrapolation_widget
        self.widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.widget.left_control_widget.composition_widget.add_element('O', 4)


    @unittest.skip('extrapolation Widget needs to be worked on!')
    def test_activating_extrapolation(self):
        # without extrapolation S(Q) should have no values below
        q, sq = self.data.sq_spectrum.data
        self.assertGreater(q[0], 1)

        # when turning extrapolation on, it should automatically interpolate sq of to zero and recalculate everything

        QTest.mouseClick(self.extrapolation_widget.activate_cb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2, self.extrapolation_widget.activate_cb.height() / 2))
        QtGui.QApplication.processEvents()
        self.assertTrue(self.extrapolation_widget.activate_cb.isChecked())

        q, sq = self.data.sq_spectrum.data
        self.assertLess(q[0], 1)

        # using a linear extrapolation to zero the sum between 0 and 0.5 should be always different from 0:
        self.assertNotAlmostEqual(np.sum(sq[np.where(q < 0.4)]), 0)

        # now switching on spline extrapolation and test for 0 values below the cutoff
        QTest.mouseClick(self.extrapolation_widget.spline_extrapolation_rb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2, self.extrapolation_widget.spline_extrapolation_rb.height() / 2))
        QtGui.QApplication.processEvents()
        self.assertTrue(self.extrapolation_widget.spline_extrapolation_rb.isChecked())

        q, sq = self.data.sq_spectrum.data
        self.assertAlmostEqual(np.sum(sq[np.where(q < 0.5)]), 0)

    def test_extrapolation_parameters(self):
        QTest.mouseClick(self.extrapolation_widget.activate_cb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2, self.extrapolation_widget.activate_cb.height() / 2))
        QTest.mouseClick(self.extrapolation_widget.spline_extrapolation_rb, QtCore.Qt.LeftButton,
                         pos=QtCore.QPoint(2, self.extrapolation_widget.spline_extrapolation_rb.height() / 2))
        QtGui.QApplication.processEvents()

        self.extrapolation_widget.spline_extrapolation_cutoff_txt.setText('')
        QTest.keyClicks(self.extrapolation_widget.spline_extrapolation_cutoff_txt, '0.7')
        QTest.keyClick(self.extrapolation_widget.spline_extrapolation_cutoff_txt, QtCore.Qt.Key_Enter)
        QtGui.QApplication.processEvents()
        q, sq = self.data.sq_spectrum.data
        self.assertAlmostEqual(np.sum(sq[np.where(q < 0.6)]), 0)

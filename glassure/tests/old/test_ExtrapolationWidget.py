# -*- coding: utf8 -*-

import unittest
import os

import numpy as np

from gui.qt import QtCore, QtGui, QTest
from gui.controller.gui_controller import GlassureController

from tests.utility import click_checkbox, set_widget_text

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


class ExtrapolationWidgetTest(unittest.TestCase):
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
        self.controller = GlassureController()
        self.controller.load_data(data_path('Mg2SiO4_ambient.xy'))
        self.controller.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))
        self.data = self.controller.model
        self.widget = self.controller.main_widget
        self.extrapolation_widget = self.widget.left_control_widget.extrapolation_widget
        self.widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.widget.left_control_widget.composition_widget.add_element('O', 4)

    def test_activating_extrapolation(self):
        if self.extrapolation_widget.activate_cb.isChecked():
            click_checkbox(self.extrapolation_widget.activate_cb)

        # without extrapolation S(Q) should have no values below
        q, sq = self.data.sq_spectrum.data
        self.assertGreater(q[0], 1)

        # when turning extrapolation on, it should automatically interpolate sq of to zero and recalculate everything
        # by default a Step function should be used
        click_checkbox(self.extrapolation_widget.activate_cb)

        self.assertTrue(self.extrapolation_widget.activate_cb.isChecked())

        q, sq = self.data.sq_spectrum.limit(0,1).data
        self.assertLess(q[0], 0.1)
        self.assertEqual(np.sum(sq), 0)

    def test_different_extrapolation_methods(self):
        if not self.extrapolation_widget.activate_cb.isChecked():
            click_checkbox(self.extrapolation_widget.activate_cb)

        # next we activate the linear Extrapolation method to see how this changes the g(r)
        # using a linear extrapolation to zero the sum between 0 and 0.5 should be always different from 0:
        click_checkbox(self.extrapolation_widget.linear_extrapolation_rb)
        q, sq = self.data.sq_spectrum.limit(0, 1).data

        self.assertNotAlmostEqual(np.sum(sq[np.where(q < 0.4)]), 0)

        # now switching on spline extrapolation and see how this effects the pattern
        prev_q, prev_sq = self.data.sq_spectrum.limit(0, 2).data
        click_checkbox(self.extrapolation_widget.spline_extrapolation_rb)
        after_q, after_sq = self.data.sq_spectrum.limit(0, 2).data

        self.assertFalse(np.array_equal(prev_sq, after_sq))

        # and last but not least the polynomial extrapolation version:
        prev_q, prev_sq = self.data.sq_spectrum.limit(0, 2).data
        click_checkbox(self.extrapolation_widget.poly_extrapolation_rb)
        after_q, after_sq = self.data.sq_spectrum.limit(0, 2).data

        self.assertFalse(np.array_equal(prev_sq, after_sq))


    def test_polynomial_parameters(self):
        if not self.extrapolation_widget.activate_cb.isChecked():
            click_checkbox(self.extrapolation_widget.activate_cb)

        click_checkbox(self.extrapolation_widget.poly_extrapolation_rb)

        # lets change the q_Max parameter and see that it does affect the pattern
        prev_q, prev_sq = self.data.sq_spectrum.limit(0, 2).data
        set_widget_text(self.extrapolation_widget.q_max_txt, 1.5)
        after_q, after_sq = self.data.sq_spectrum.limit(0, 2).data

        self.assertFalse(np.array_equal(prev_sq, after_sq))

        # there seems to be a strange connection between the two parts, lets use the replace option and see the change
        prev_q, prev_sq = self.data.sq_spectrum.limit(0, 2).data
        click_checkbox(self.extrapolation_widget.replace_cb)
        after_q, after_sq = self.data.sq_spectrum.limit(0, 2).data

        self.assertFalse(np.array_equal(prev_sq, after_sq))

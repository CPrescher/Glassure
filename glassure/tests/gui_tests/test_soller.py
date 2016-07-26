# -*- coding: utf8 -*-

import os
import unittest

from glassure.gui.controller.glassure import GlassureController
from glassure.gui.qt import QtGui
from glassure.tests.gui_tests.utility import click_button, click_checkbox, array_almost_equal

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


class SollerWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtGui.QApplication.instance()
        if cls.app is None:
            cls.app = QtGui.QApplication([])

    def setUp(self):
        self.controller = GlassureController()
        self.widget = self.controller.main_widget
        self.soller_widget = self.widget.soller_widget
        self.model = self.controller.model

        self.widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.widget.left_control_widget.composition_widget.add_element('O', 4)

        self.controller.load_data(data_path('Mg2SiO4_ambient.xy'))
        self.controller.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))

    def test_activate_soller_correction(self):
        _, prev_sq = self.model.sq_pattern.data
        click_checkbox(self.soller_widget.activate_cb)

        _, new_sq = self.model.sq_pattern.data

        self.assertFalse(array_almost_equal(prev_sq, new_sq))

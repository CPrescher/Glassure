# -*- coding: utf-8 -*-

from glassure.gui.controller.glassure import GlassureController
from .utility import click_checkbox, array_almost_equal, QtTest, prepare_file_loading


class SollerWidgetTest(QtTest):
    def setUp(self):
        self.controller = GlassureController()
        self.widget = self.controller.main_widget
        self.soller_widget = self.widget.soller_widget
        self.model = self.controller.model

        self.widget.left_control_widget.composition_widget.add_element('Mg', 2)
        self.widget.left_control_widget.composition_widget.add_element('Si', 1)
        self.widget.left_control_widget.composition_widget.add_element('O', 4)

        prepare_file_loading('Mg2SiO4_ambient.xy')
        self.controller.load_data()
        prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
        self.controller.load_bkg()

    def test_activate_soller_correction(self):
        _, prev_sq = self.model.sq_pattern.data
        click_checkbox(self.soller_widget.activate_cb)

        _, new_sq = self.model.sq_pattern.data

        self.assertFalse(array_almost_equal(prev_sq, new_sq))

# -*- coding: utf-8 -*-
from glassure.gui.controller.glassure import GlassureController
from .utility import click_button, QtTest


class ConfigurationWidgetTest(QtTest):
    def setUp(self):
        self.main_controller = GlassureController()
        self.main_widget = self.main_controller.main_widget
        self.configuration_widget = self.main_widget.configuration_widget
        self.model = self.main_controller.model

    def test_freeze_configuration(self):
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 1)

        click_button(self.configuration_widget.freeze_btn)
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 2)
        self.assertEqual(self.configuration_widget.configuration_tw.columnCount(), 3)

        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 4)

    def test_remove_configuration(self):
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 1)
        click_button(self.configuration_widget.remove_btn)
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 1)

        click_button(self.configuration_widget.freeze_btn)
        click_button(self.configuration_widget.freeze_btn)

        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 3)

        click_button(self.configuration_widget.remove_btn)
        self.assertEqual(self.configuration_widget.configuration_tw.rowCount(), 2)

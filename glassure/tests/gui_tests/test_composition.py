# -*- coding: utf-8 -*-
from copy import copy
import numpy as np

from qtpy import QtCore
from qtpy.QtTest import QTest
from glassure.gui.controller.glassure import GlassureController
from .utility import prepare_file_loading, QtTest


class CompositionGroupBoxTest(QtTest):
    def setUp(self):
        self.controller = GlassureController()
        self.widget = self.controller.main_widget
        self.composition_widget = self.widget.left_control_widget.composition_widget

        prepare_file_loading('Mg2SiO4_ambient.xy')
        self.controller.load_data()
        prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
        self.controller.load_bkg()

    def test_adding_and_deleting_elements(self):
        QTest.mouseClick(self.composition_widget.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 1)
        QTest.mouseClick(self.composition_widget.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 2)
        QTest.mouseClick(self.composition_widget.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 3)

        self.composition_widget.composition_tw.setCurrentCell(0, 1)
        QTest.mouseClick(self.composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 2)
        QTest.mouseClick(self.composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 1)
        QTest.mouseClick(self.composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 0)
        QTest.mouseClick(self.composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_widget.composition_tw.rowCount(), 0)

    def test_getting_composition(self):
        self.composition_widget.add_element('Si', 1)
        self.composition_widget.add_element('Mg', 1)
        self.composition_widget.add_element('O', 3)

        expected_composition = {
            'Si': 1,
            'Mg': 1,
            'O': 3
        }

        self.assertEqual(self.composition_widget.get_composition(), expected_composition)

    def test_changing_composition(self):
        self.composition_widget.add_element('Si', 1)
        self.composition_widget.add_element('Mg', 1)
        self.composition_widget.add_element('O', 3)

        composition = {
            'Si': 1,
            'Mg': 1,
            'O': 3
        }
        self.assertEqual(self.composition_widget.get_composition(), composition)

        self.composition_widget.composition_tw.item(0, 1).setText('2')
        composition['Si'] = 2
        self.assertEqual(self.composition_widget.get_composition(), composition)

        element_cb = self.composition_widget.composition_tw.cellWidget(0, 0)
        element_cb.setCurrentIndex(element_cb.findText('Ge'))

        new_composition = {
            'Ge': 2,
            'Mg': 1,
            'O': 3,
        }
        self.assertEqual(self.composition_widget.get_composition(), new_composition)

    def test_changing_data_source_with_available_elements(self):
        composition = {
            'Si': 1,
            'Mg': 2,
            'O': 4
        }

        self.composition_widget.set_composition(composition)
        self.controller.update_model()

        sq_hajdu = copy(self.controller.model.sq_pattern)
        self.composition_widget.source_cb.setCurrentIndex(1)
        self.assertEqual(composition, self.composition_widget.get_composition())

        sq_brown_hubbell = copy(self.controller.model.sq_pattern)
        self.assertFalse(np.allclose(sq_hajdu.y, sq_brown_hubbell.y))

    def test_changing_data_source_with_unavailable_elements(self):
        self.composition_widget.source_cb.setCurrentIndex(1)
        composition = {
            'Si': 1,
            'Mg': 2,
            'Hg': 4
        }

        self.composition_widget.set_composition(composition)
        self.controller.update_model()

        self.composition_widget.source_cb.setCurrentIndex(0)
        new_composition = self.composition_widget.get_composition()
        self.assertEqual({'Mg': 2, 'Si': 1}, new_composition)

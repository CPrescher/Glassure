# -*- coding: utf-8 -*-
from qtpy import QtCore
from qtpy.QtTest import QTest
from glassure.gui.controller.glassure import GlassureController
from .utility import prepare_file_loading, QtTest


class CompositionGroupBoxTest(QtTest):
    def setUp(self):
        self.controller = GlassureController()
        self.widget = self.controller.main_widget
        self.composition_gb = self.widget.left_control_widget.composition_widget

        prepare_file_loading('Mg2SiO4_ambient.xy')
        self.controller.load_data()
        prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
        self.controller.load_bkg()

    def test_adding_and_deleting_elements(self):
        QTest.mouseClick(self.composition_gb.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 1)
        QTest.mouseClick(self.composition_gb.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 2)
        QTest.mouseClick(self.composition_gb.add_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 3)

        self.composition_gb.composition_tw.setCurrentCell(0, 1)
        QTest.mouseClick(self.composition_gb.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 2)
        QTest.mouseClick(self.composition_gb.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 1)
        QTest.mouseClick(self.composition_gb.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 0)
        QTest.mouseClick(self.composition_gb.delete_element_btn, QtCore.Qt.LeftButton)
        self.assertEqual(self.composition_gb.composition_tw.rowCount(), 0)

    def test_getting_composition(self):
        self.composition_gb.add_element('Si', 1)
        self.composition_gb.add_element('Mg', 1)
        self.composition_gb.add_element('O', 3)

        expected_composition = {
            'Si': 1,
            'Mg': 1,
            'O': 3
        }

        self.assertEqual(self.composition_gb.get_composition(), expected_composition)

    def test_changing_composition(self):
        self.composition_gb.add_element('Si', 1)
        self.composition_gb.add_element('Mg', 1)
        self.composition_gb.add_element('O', 3)

        composition = {
            'Si': 1,
            'Mg': 1,
            'O': 3
        }
        self.assertEqual(self.composition_gb.get_composition(), composition)

        self.composition_gb.composition_tw.item(0, 1).setText('2')
        composition['Si'] = 2
        self.assertEqual(self.composition_gb.get_composition(), composition)

        element_cb = self.composition_gb.composition_tw.cellWidget(0, 0)
        element_cb.setCurrentIndex(element_cb.findText('Ge'))

        new_composition = {
            'Ge': 2,
            'Mg': 1,
            'O': 3,
        }
        self.assertEqual(self.composition_gb.get_composition(), new_composition)

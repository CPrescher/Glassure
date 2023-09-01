# -*- coding: utf-8 -*-
from copy import copy
import numpy as np
import pytest

from qtpy import QtCore
from .utility import prepare_file_loading, set_widget_text


@pytest.fixture
def setup(main_controller):
    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()


def test_adding_and_deleting_elements(composition_widget, model, qtbot):
    qtbot.mouseClick(composition_widget.add_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 1
    qtbot.mouseClick(composition_widget.add_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 2
    qtbot.mouseClick(composition_widget.add_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 3
    composition_widget.composition_tw.setCurrentCell(0, 1)

    qtbot.mouseClick(composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 2
    assert len(model.composition) == 2
    qtbot.mouseClick(composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 1
    assert len(model.composition) == 1
    qtbot.mouseClick(composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 0
    assert len(model.composition) == 0
    qtbot.mouseClick(composition_widget.delete_element_btn, QtCore.Qt.LeftButton)
    assert composition_widget.composition_tw.rowCount() == 0


def test_getting_composition(composition_widget):
    composition_widget.add_element('Si', 1)
    composition_widget.add_element('Mg', 1)
    composition_widget.add_element('O', 3)

    expected_composition = {
        'Si': 1,
        'Mg': 1,
        'O': 3
    }

    assert composition_widget.get_composition() == expected_composition


def test_changing_composition(composition_widget):
    composition_widget.add_element('Si', 1)
    composition_widget.add_element('Mg', 1)
    composition_widget.add_element('O', 3)

    expected_composition = {
        'Si': 1,
        'Mg': 1,
        'O': 3
    }

    assert composition_widget.get_composition() == expected_composition

    composition_widget.composition_tw.item(0, 1).setText('2')
    expected_composition['Si'] = 2
    assert composition_widget.get_composition() == expected_composition

    element_cb = composition_widget.composition_tw.cellWidget(0, 0)
    element_cb.setCurrentIndex(element_cb.findText('Ge'))

    new_composition = {
        'Ge': 2,
        'Mg': 1,
        'O': 3,
    }
    assert composition_widget.get_composition() == new_composition


def test_changing_data_source_with_available_elements(setup, main_controller, composition_widget):
    composition = {
        'Si': 1,
        'Mg': 2,
        'O': 4
    }

    composition_widget.set_composition(composition)
    main_controller.update_model()

    sq_hajdu = copy(main_controller.model.sq_pattern)
    composition_widget.source_cb.setCurrentIndex(1)
    main_controller.update_model()

    assert np.allclose(sq_hajdu.data[1], main_controller.model.sq_pattern.data[1], atol=1.e-2)


def test_changing_data_source_with_unavailable_elements(setup, main_controller, composition_widget):
    composition_widget.source_cb.setCurrentIndex(1)
    assert main_controller.model.sf_source == 'brown_hubbell'
    composition = {
        'Si': 1,
        'Mg': 2,
        'Hg': 4
    }

    composition_widget.set_composition(composition)
    main_controller.update_model()
    composition_widget.source_cb.setCurrentIndex(0)

    assert {'Mg': 2, 'Si': 1} == main_controller.model.composition

    new_composition = composition_widget.get_composition()
    assert {'Mg': 2, 'Si': 1} == new_composition


def test_inserting_density_with_comma_as_decimal_separator(setup, composition_widget):
    set_widget_text(composition_widget.density_txt, '3,4')
    assert composition_widget.density_txt.value() == 3.4

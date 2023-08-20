# -*- coding: utf-8 -*-
from qtpy.QtCore import Qt

from glassure.gui.widgets.glassure_widget import GlassureWidget
from .utility import set_widget_text

def test_freeze_configuration(configuration_widget, qtbot):
    assert configuration_widget.configuration_tw.rowCount() == 1

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2
    assert configuration_widget.configuration_tw.columnCount() == 3

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 4


def test_remove_configuration(configuration_widget, qtbot):
    assert configuration_widget.configuration_tw.rowCount() == 1
    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 1

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)

    assert configuration_widget.configuration_tw.rowCount() == 3

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2


def test_remove_configuration_changes_to_correct_configuration(
        main_widget: GlassureWidget, configuration_widget, model,
        qtbot):

    assert configuration_widget.configuration_tw.rowCount() == 1
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    set_widget_text(main_widget.q_max_txt, '13')
    assert model.q_max == 13

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    set_widget_text(main_widget.q_max_txt, '14')
    assert model.q_max == 14

    assert configuration_widget.configuration_tw.rowCount() == 3

    configuration_widget.configuration_tw.setCurrentCell(0, 0)
    assert model.q_max == 10
    assert model.configuration_ind == 0

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2
    assert model.configuration_ind == 0
    assert model.q_max == 13
    assert main_widget.q_max_txt.text() == '13.0'

    configuration_widget.configuration_tw.setCurrentCell(1, 0)
    assert model.configuration_ind == 1
    assert model.q_max == 14
    assert main_widget.q_max_txt.text() == '14.0'

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 1
    assert model.configuration_ind == 0
    assert model.q_max == 13
    assert main_widget.q_max_txt.text() == '13.0'

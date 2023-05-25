# -*- coding: utf-8 -*-
from qtpy.QtCore import Qt


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

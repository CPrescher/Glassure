# -*- coding: utf8 -*-

from gui.qt import QtGui, QtCore, QTest

def set_widget_text(widget, txt):
    txt = str(txt)
    QTest.keyClicks(widget, txt)
    QTest.keyClick(widget, QtCore.Qt.Key_Enter)
    QtGui.QApplication.processEvents()


def click_checkbox(checkbox_widget):
    QTest.mouseClick(checkbox_widget, QtCore.Qt.LeftButton, pos=QtCore.QPoint(2, checkbox_widget.height() / 2))
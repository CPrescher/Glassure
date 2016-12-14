# -*- coding: utf8 -*-
import os
import unittest

import numpy as np
from mock import MagicMock

from glassure.gui.qt import QtCore, QTest, QtWidgets

unittest_data_path = os.path.join(os.path.dirname(__file__), '..', 'data')


class QtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication([])


def data_path(filename):
    return os.path.join(unittest_data_path, filename)


def prepare_file_loading(filename):
    QtWidgets.QFileDialog.getOpenFileName = MagicMock(return_value=data_path(filename))


def set_widget_text(widget, txt):
    widget.setText('')
    txt = str(txt)
    QTest.keyClicks(widget, txt)
    QTest.keyClick(widget, QtCore.Qt.Key_Enter)
    QtWidgets.QApplication.processEvents()


def click_checkbox(checkbox_widget):
    QTest.mouseClick(checkbox_widget, QtCore.Qt.LeftButton, pos=QtCore.QPoint(2, checkbox_widget.height() / 2))


def click_button(widget):
    QTest.mouseClick(widget, QtCore.Qt.LeftButton)


def array_almost_equal(array1, array2, places=3):
    return np.sum(array1 - array2) / len(array1) < 1 / (places * 10.)

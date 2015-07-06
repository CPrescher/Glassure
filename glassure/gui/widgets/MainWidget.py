# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
__version__ = '0.1'

import sys
import os

from PyQt4 import QtGui, QtCore

from gui.widgets.SpectrumWidget import SpectrumWidget
from .ControlWidget import LeftControlWidget, RightControlWidget


class MainWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)
        self.horizontal_layout = QtGui.QHBoxLayout(self)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)

        self.spectrum_widget = SpectrumWidget()
        self.left_control_widget = LeftControlWidget()
        self.right_control_widget = RightControlWidget()

        self.left_control_scroll_area = QtGui.QScrollArea()
        self.left_control_scroll_area.setWidget(self.left_control_widget)
        self.left_control_scroll_area.setWidgetResizable(True)

        self.left_control_scroll_area.setMaximumWidth(300)
        self.left_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.right_control_scroll_area = QtGui.QScrollArea()
        self.right_control_scroll_area.setWidget(self.right_control_widget)
        self.right_control_scroll_area.setWidgetResizable(True)

        self.right_control_scroll_area.setMaximumWidth(300)
        self.right_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.horizontal_layout.addWidget(self.left_control_scroll_area)
        self.horizontal_layout.addWidget(self.spectrum_widget)
        self.horizontal_layout.addWidget(self.right_control_scroll_area)

        self.horizontal_layout.setStretch(0, 0)
        self.horizontal_layout.setStretch(1, 100)
        self.horizontal_layout.setStretch(2, 0)

        self.setLayout(self.horizontal_layout)

        self.load_stylesheet()

        self.setWindowTitle("Glassure v{}".format(__version__))

    def show(self):
        QtGui.QWidget.show(self)
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.activateWindow()
        self.raise_()

    def load_stylesheet(self):
        stylesheet_file = open(os.path.join(module_path(), "DioptasStyle.qss"), 'r')
        stylesheet_str = stylesheet_file.read()
        self.setStyleSheet(stylesheet_str)


def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    return os.path.dirname(unicode(__file__, encoding))
# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
__version__ = '0.1'

import sys
import os
from PyQt4 import QtGui, QtCore

from .SpectrumWidget import SpectrumWidget
from .ControlWidget import ControlWidget


class MainWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)
        self.horizontal_layout = QtGui.QHBoxLayout(self)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)

        self.spectrum_widget = SpectrumWidget()
        self.control_widget = ControlWidget()
        self.control_widget.setMaximumWidth(240)

        self.horizontal_layout.addWidget(self.spectrum_widget)
        self.horizontal_layout.addWidget(self.control_widget)

        self.horizontal_layout.setStretch(0, 10)
        self.horizontal_layout.setStretch(1, 0)

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
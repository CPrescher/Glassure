# -*- coding: utf8 -*-

try:
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtTest import QTest
    Signal = QtCore.pyqtSignal
except ImportError:
    from PySide import QtCore, QtGui
    from PySide.QtTest import QTest
    Signal = QtCore.Signal
# -*- coding: utf-8 -*-

# from qtpy import QtCore, QtGui, QtWidgets
# from qtpy.QtTest import QTest
# Signal = QtCore.Signal

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    Signal = QtCore.pyqtSignal
    from PyQt5.QtTest import QTest
except ImportError:
    from PyQt4 import QtCore, QtGui
    QtWidgets = QtGui
    Signal = QtCore.pyqtSignal
    from PyQt4.QtTest import QTest

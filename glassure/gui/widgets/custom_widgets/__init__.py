# -*- coding: utf8 -*-

from ...qt import QtGui
from .box import ExpandableBox
from .lines import HorizontalLine
from .spectrum_widget import SpectrumWidget


def VerticalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

def HorizontalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)

class NumberTextField(QtGui.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(NumberTextField, self).__init__(*args, **kwargs)
        self.setValidator(QtGui.QDoubleValidator())
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

class FlatButton(QtGui.QPushButton):
    def __init__(self, *args):
        super(FlatButton, self).__init__(*args)
        self.setFlat(True)


class CheckableFlatButton(QtGui.QPushButton):
    def __init__(self, *args):
        super(CheckableFlatButton, self).__init__(*args)
        self.setFlat(True)
        self.setCheckable(True)

class ListTableWidget(QtGui.QTableWidget):
    def __init__(self, columns=3):
        super(ListTableWidget, self).__init__()

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setColumnCount(columns)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
# -*- coding: utf8 -*-

from ...qt import QtGui, QtCore, Signal
from .box import ExpandableBox
from .lines import HorizontalLine
from .spectrum import SpectrumWidget


def VerticalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)


def HorizontalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)


class NumberTextField(QtGui.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(NumberTextField, self).__init__(*args, **kwargs)
        self.setValidator(QtGui.QDoubleValidator())
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)


class LabelAlignRight(QtGui.QLabel):
    def __init__(self, *args, **kwargs):
        super(LabelAlignRight, self).__init__(*args, **kwargs)
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


class ValueLabelTxtPair(QtGui.QWidget):
    editingFinished = Signal()

    def __init__(self, label_str, value_init, unit_str, layout, layout_row=0, layout_col=0, parent=None):
        super(ValueLabelTxtPair, self).__init__(parent)

        self.desc_lbl = LabelAlignRight(label_str)
        self.value_txt = NumberTextField(str(value_init))
        self.unit_lbl = LabelAlignRight(unit_str)

        self.layout = layout

        self.layout.addWidget(self.desc_lbl, layout_row, layout_col)
        self.layout.addWidget(self.value_txt, layout_row, layout_col + 1)
        self.layout.addWidget(self.unit_lbl, layout_row, layout_col + 2)

        self.value_txt.editingFinished.connect(self.editingFinished.emit)

        self.setText = self.value_txt.setText

    def get_value(self):
        return float(str(self.value_txt.text()))

    def set_value(self, value):
        self.value_txt.setText(str(value))



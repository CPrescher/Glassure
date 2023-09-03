# -*- coding: utf-8 -*-

from qtpy import QtCore, QtGui, QtWidgets
from .lines import HorizontalLine

Signal = QtCore.Signal


def VerticalSpacerItem():
    return QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum,
                                 QtWidgets.QSizePolicy.Expanding)


def HorizontalSpacerItem():
    return QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding,
                                 QtWidgets.QSizePolicy.Ex)


class CommaDoubleValidator(QtGui.QDoubleValidator):
    """
    This class is used to validate the number input of a NumberTextfield
    widget. It allows the user to input a number with a comma or a dot as
    decimal separator.
    """

    def validate(self, text, pos):
        text = text.replace(",", ".")
        return super(CommaDoubleValidator, self).validate(text, pos)


class FloatLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(FloatLineEdit, self).__init__(*args, **kwargs)
        self.setValidator(CommaDoubleValidator())
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def text(self):
        return super(FloatLineEdit, self).text().replace(",", ".")

    def value(self):
        return float(self.text())


class IntegerLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(IntegerLineEdit, self).__init__(*args, **kwargs)
        self.setValidator(QtGui.QIntValidator())
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def value(self):
        return int(self.text())


class LabelAlignRight(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        super(LabelAlignRight, self).__init__(*args, **kwargs)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)


class FlatButton(QtWidgets.QPushButton):
    def __init__(self, *args):
        super(FlatButton, self).__init__(*args)
        self.setFlat(True)

    def text(self):
        return super(FloatLineEdit, self).text().replace(",", ".")

    def value(self):
        return float(self.text())


class CheckableFlatButton(QtWidgets.QPushButton):
    def __init__(self, *args):
        super(CheckableFlatButton, self).__init__(*args)
        self.setFlat(True)
        self.setCheckable(True)


class ListTableWidget(QtWidgets.QTableWidget):
    def __init__(self, columns=3):
        super(ListTableWidget, self).__init__()

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setColumnCount(columns)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)


class ValueLabelTxtPair(QtWidgets.QWidget):
    editingFinished = Signal()

    def __init__(self, label_str, value_init, unit_str, layout, layout_row=0, layout_col=0, parent=None):
        super(ValueLabelTxtPair, self).__init__(parent)

        self.desc_lbl = LabelAlignRight(label_str)
        self.value_txt = FloatLineEdit(str(value_init))
        self.unit_lbl = LabelAlignRight(unit_str)

        self.layout = layout

        self.layout.addWidget(self.desc_lbl, layout_row, layout_col)
        self.layout.addWidget(self.value_txt, layout_row, layout_col + 1)
        self.layout.addWidget(self.unit_lbl, layout_row, layout_col + 2)

        self.value_txt.editingFinished.connect(self.editingFinished.emit)

    def get_value(self):
        return float(str(self.value_txt.text()))

    def set_value(self, value):
        self.value_txt.setText(str(value))

    def setText(self, new_str):
        self.value_txt.setText(new_str)


class DragSlider(QtWidgets.QSlider):
    dragChanged = Signal(int)

    def __init__(self, parent=None):
        super(DragSlider, self).__init__(parent)

        self.setRange(-100, 100)
        self.setSingleStep(1)
        self.setPageStep(0)

        self._drag_value = 0

        self.setOrientation(QtCore.Qt.Horizontal)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.send_value)

        self.sliderPressed.connect(self.start_drag)
        self.sliderReleased.connect(self.stop_drag)
        super(DragSlider, self).valueChanged.connect(self._update_value)

    def _update_value(self, value):
        self._drag_value = value

    def reset_value(self):
        self._drag_value = 0

    def start_drag(self):
        if not self.timer.isActive():
            self.timer.start(100)

    def send_value(self):
        self.dragChanged.emit(self._drag_value)

    def stop_drag(self):
        self.timer.stop()
        self.blockSignals(True)
        self.setValue(0)
        self.blockSignals(False)

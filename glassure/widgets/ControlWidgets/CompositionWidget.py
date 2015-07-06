# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
from PyQt4 import QtCore, QtGui

from model.ScatteringFactors import scattering_factor_param


class CompositionWidget(QtGui.QWidget):
    composition_changed = QtCore.pyqtSignal(dict, float)

    def __init__(self, *args):
        super(CompositionWidget, self).__init__(*args)

        self._create_widgets()
        self._create_layout()
        self._style_widgets()

    def _create_widgets(self):
        self.add_element_btn = QtGui.QPushButton("Add")
        self.delete_element_btn = QtGui.QPushButton("Delete")

        self.density_lbl = QtGui.QLabel("Density:")
        self.density_txt = QtGui.QLineEdit("2.2")
        self.density_atomic_units_lbl = QtGui.QLabel("")

        self.composition_tw = QtGui.QTableWidget()
        self.composition_tw.cellChanged.connect(self.emit_composition_changed_signal)

    def _create_layout(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setSpacing(15)
        self.button_layout.addWidget(self.add_element_btn)
        self.button_layout.addWidget(self.delete_element_btn)

        self.density_layout = QtGui.QGridLayout()
        self.density_layout.addWidget(self.density_lbl, 0, 0)
        self.density_layout.addWidget(self.density_txt, 0, 1)
        self.density_layout.addWidget(QtGui.QLabel('g/cm^3'), 0, 2)
        self.density_layout.addWidget(self.density_atomic_units_lbl, 1, 1)
        self.density_layout.addWidget(QtGui.QLabel('at/A^3'), 1, 2)

        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.composition_tw)
        self.main_layout.addLayout(self.density_layout)

        self.setLayout(self.main_layout)


    def _style_widgets(self):
        self.density_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.density_atomic_units_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.density_txt.setAlignment(QtCore.Qt.AlignRight)
        self.density_txt.setValidator(QtGui.QDoubleValidator())
        self.density_txt.editingFinished.connect(self.emit_composition_changed_signal)
        self.density_txt.setMaximumWidth(100)

        self.composition_tw.setColumnCount(2)
        self.composition_tw.horizontalHeader().setVisible(False)
        self.composition_tw.verticalHeader().setVisible(False)
        self.composition_tw.setColumnWidth(0, 80)
        self.composition_tw.setColumnWidth(1, 80)
        self.composition_tw.setItemDelegate(TextDoubleDelegate(self))

    def add_element(self, element=None, value=None):
        current_rows = self.composition_tw.rowCount()
        self.composition_tw.setRowCount(current_rows + 1)
        self.composition_tw.blockSignals(True)
        element_cb = QtGui.QComboBox(self)
        element_cb.setStyle(QtGui.QStyleFactory.create('cleanlooks'))

        for ind, ele in enumerate(scattering_factor_param.index):
            element_cb.insertItem(ind, ele)

        if element is not None:
            element_cb.setCurrentIndex(element_cb.findText(element))
        self.composition_tw.setCellWidget(current_rows, 0, element_cb)

        element_cb.currentIndexChanged.connect(self.emit_composition_changed_signal)
        if value is not None:
            value_item = QtGui.QTableWidgetItem(str(value))
        else:
            value_item = QtGui.QTableWidgetItem(str(1))
        value_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.composition_tw.setItem(current_rows, 1, value_item)
        self.composition_tw.blockSignals(False)
        self.emit_composition_changed_signal()

    def delete_element(self, ind):
        self.composition_tw.blockSignals(True)
        self.composition_tw.removeRow(ind)
        self.composition_tw.blockSignals(False)
        self.emit_composition_changed_signal()

    def get_composition(self):
        composition = {}
        for row_ind in range(self.composition_tw.rowCount()):
            cb_item = self.composition_tw.cellWidget(row_ind, 0)
            value_item = self.composition_tw.item(row_ind, 1)
            composition[str(cb_item.currentText())] = float(str(value_item.text()))
        return composition

    def get_density(self):
        return float(str(self.density_txt.text()))

    def emit_composition_changed_signal(self):
        self.composition_changed.emit(self.get_composition(), self.get_density())


class TextDoubleDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, parent):
        super(TextDoubleDelegate, self).__init__(parent)

    def createEditor(self, parent, _, model):
        self.editor = QtGui.QLineEdit(parent)
        self.editor.setFrame(False)
        self.editor.setValidator(QtGui.QDoubleValidator())
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return self.editor

    def setEditorData(self, parent, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        if value.toString() != '':
            self.editor.setText("{:g}".format(float(str(value.toString()))))

    def setModelData(self, parent, model, index):
        value = self.editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, _):
        editor.setGeometry(option.rect)
# -*- coding: utf-8 -*-

from qtpy import QtCore, QtGui, QtWidgets
from ....core.scattering_factors import calculators, sources

Signal = QtCore.Signal


class CompositionWidget(QtWidgets.QWidget):
    composition_changed = Signal(dict, float)

    def __init__(self, *args):
        super(CompositionWidget, self).__init__(*args)

        self._create_widgets()
        self._create_layout()
        self._style_widgets()

    def _create_widgets(self):
        self.source_lbl = QtWidgets.QLabel("Source:")
        self.source_cb = QtWidgets.QComboBox()
        self.source_cb.addItems(sources)
        self.source_cb.setCurrentIndex(0)

        self.add_element_btn = QtWidgets.QPushButton("Add")
        self.delete_element_btn = QtWidgets.QPushButton("Delete")

        self.density_lbl = QtWidgets.QLabel("Density:")
        self.density_txt = QtWidgets.QLineEdit("2.2")
        self.density_atomic_units_lbl = QtWidgets.QLabel("")

        self.composition_tw = QtWidgets.QTableWidget()
        self.composition_tw.cellChanged.connect(self.emit_composition_changed_signal)

    def _create_layout(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.source_layout = QtWidgets.QHBoxLayout()
        self.source_layout.setSpacing(5)
        self.source_layout.addWidget(self.source_lbl)
        self.source_layout.addWidget(self.source_cb)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.setSpacing(15)
        self.button_layout.addWidget(self.add_element_btn)
        self.button_layout.addWidget(self.delete_element_btn)

        self.density_layout = QtWidgets.QGridLayout()
        self.density_layout.addWidget(self.density_lbl, 0, 0)
        self.density_layout.addWidget(self.density_txt, 0, 1)
        self.density_layout.addWidget(QtWidgets.QLabel('g/cm^3'), 0, 2)
        self.density_layout.addWidget(self.density_atomic_units_lbl, 1, 1)
        self.density_layout.addWidget(QtWidgets.QLabel('at/A^3'), 1, 2)

        self.main_layout.addLayout(self.source_layout)
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.composition_tw)
        self.main_layout.addLayout(self.density_layout)

        self.setLayout(self.main_layout)

    def _style_widgets(self):

        self.source_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

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
        element_cb = QtWidgets.QComboBox(self)
        element_cb.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))

        for ind, ele in enumerate(calculators[self.source_cb.currentText()].elements):
            element_cb.insertItem(ind, ele)

        if element is not None:
            element_cb.setCurrentIndex(element_cb.findText(element))
        self.composition_tw.setCellWidget(current_rows, 0, element_cb)

        element_cb.currentIndexChanged.connect(self.emit_composition_changed_signal)
        if value is not None:
            value_item = QtWidgets.QTableWidgetItem(str(value))
        else:
            value_item = QtWidgets.QTableWidgetItem(str(1))
        value_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.composition_tw.setItem(current_rows, 1, value_item)
        self.composition_tw.blockSignals(False)
        self.emit_composition_changed_signal()

    def delete_element(self, ind):
        self.composition_tw.blockSignals(True)
        self.composition_tw.removeRow(ind)
        self.composition_tw.blockSignals(False)
        self.emit_composition_changed_signal()

    def set_composition(self, composition):
        self.composition_tw.blockSignals(True)
        self.blockSignals(True)
        self.composition_tw.setRowCount(0)
        for element, value in composition.items():
            self.add_element(element, value)
        self.composition_tw.blockSignals(False)
        self.blockSignals(False)

    def get_composition(self):
        composition = {}
        for row_ind in range(self.composition_tw.rowCount()):
            cb_item = self.composition_tw.cellWidget(row_ind, 0)
            value_item = self.composition_tw.item(row_ind, 1)
            composition[str(cb_item.currentText())] = float(str(value_item.text()))
        return composition

    def get_density(self):
        return float(str(self.density_txt.text()).replace(",", "."))

    def emit_composition_changed_signal(self):
        self.composition_changed.emit(self.get_composition(), self.get_density())


class TextDoubleDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        super(TextDoubleDelegate, self).__init__(parent)

    def createEditor(self, parent, _, model):
        self.editor = QtWidgets.QLineEdit(parent)
        self.editor.setFrame(False)
        self.editor.setValidator(QtGui.QDoubleValidator())
        self.editor.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return self.editor

    def setEditorData(self, parent, index):
        value = index.model().data(index, QtCore.Qt.EditRole)
        try:
            value = value.toString()
        except AttributeError:
            value = value

        if value != '':
            self.editor.setText("{:g}".format(float(value)))

    def setModelData(self, parent, model, index):
        value = self.editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, _):
        editor.setGeometry(option.rect)

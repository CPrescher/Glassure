# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtCore, QtGui

from ScatteringFactors import scattering_factor_param


class ControlWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(ControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setSpacing(0)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.file_widget = FileWidget()
        self.background_options_gb = BackgroundOptionsGroupBox()
        self.smooth_gb = SmoothGroupBox()
        self.composition_gb = CompositionGroupBox()
        self.calculation_gb = CalculationGroupBox()

        self.vertical_layout.addWidget(self.file_widget)
        self.vertical_layout.addWidget(self.background_options_gb)
        self.vertical_layout.addWidget(self.smooth_gb)
        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(10, 10, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.Fixed))
        self.vertical_layout.addWidget(self.composition_gb)
        self.vertical_layout.addWidget(self.calculation_gb)

        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.Expanding))
        self.setLayout(self.vertical_layout)


class FileWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(FileWidget, self).__init__(*args, **kwargs)

        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)

        self.load_data_btn = QtGui.QPushButton("Load Data")
        self.data_filename_lbl = QtGui.QLabel("None")
        self.data_filename_lbl.setAlignment(QtCore.Qt.AlignRight)
        self.load_background_btn = QtGui.QPushButton("Load Bkg")
        self.background_filename_lbl = QtGui.QLabel("None")
        self.background_filename_lbl.setAlignment(QtCore.Qt.AlignRight)
        self.plot_subtracted = QtGui.QCheckBox("Plot subtracted")
        self.plot_subtracted.setChecked(True)

        self.vertical_layout.addWidget(self.load_data_btn)
        self.vertical_layout.addWidget(self.data_filename_lbl)
        self.vertical_layout.addWidget(self.load_background_btn)
        self.vertical_layout.addWidget(self.background_filename_lbl)
        self.vertical_layout.addWidget(self.plot_subtracted)

        self.setLayout(self.vertical_layout)


class BackgroundOptionsGroupBox(QtGui.QGroupBox):
    def __init__(self, *args):
        super(BackgroundOptionsGroupBox, self).__init__(*args)

        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(3, 5, 5, 3)
        self.grid_layout.setSpacing(5)

        self.scale_lbl = QtGui.QLabel("Scale:")
        self.offset_lbl = QtGui.QLabel("Offset:")
        self.scale_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.offset_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.scale_sb = QtGui.QDoubleSpinBox()
        self.scale_sb.setValue(1.0)
        self.offset_sb = QtGui.QDoubleSpinBox()

        self.scale_sb.setAlignment(QtCore.Qt.AlignRight)
        self.offset_sb.setAlignment(QtCore.Qt.AlignRight)

        self.scale_sb.setSingleStep(0.01)
        self.offset_sb.setSingleStep(10)

        self.scale_step_txt = QtGui.QLineEdit("0.01")
        self.scale_step_txt.setMaximumWidth(60)
        self.offset_step_txt = QtGui.QLineEdit("10")
        self.offset_step_txt.setMaximumWidth(60)

        self.scale_step_txt.setAlignment(QtCore.Qt.AlignRight)
        self.offset_step_txt.setAlignment(QtCore.Qt.AlignRight)

        self.scale_step_txt.setValidator(QtGui.QDoubleValidator())
        self.offset_step_txt.setValidator(QtGui.QDoubleValidator())

        self.grid_layout.addWidget(self.scale_lbl, 0, 0)
        self.grid_layout.addWidget(self.scale_sb, 0, 1)
        self.grid_layout.addWidget(self.scale_step_txt, 0, 2)

        self.grid_layout.addWidget(self.offset_lbl, 1, 0)
        self.grid_layout.addWidget(self.offset_sb, 1, 1)
        self.grid_layout.addWidget(self.offset_step_txt, 1, 2)

        self.setLayout(self.grid_layout)


class SmoothGroupBox(QtGui.QGroupBox):
    def __init__(self, *args):
        super(SmoothGroupBox, self).__init__(*args)
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(5)

        self.smooth_lbl = QtGui.QLabel("Smooth:")
        self.smooth_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.smooth_sb = QtGui.QDoubleSpinBox()
        self.smooth_sb.setAlignment(QtCore.Qt.AlignRight)
        self.smooth_sb.setSingleStep(0.01)

        self.smooth_step_txt = QtGui.QLineEdit("0.01")
        self.smooth_step_txt.setAlignment(QtCore.Qt.AlignRight)
        self.smooth_step_txt.setValidator(QtGui.QDoubleValidator())
        self.smooth_step_txt.setMaximumWidth(60)

        self.grid_layout.addWidget(self.smooth_lbl, 0, 0)
        self.grid_layout.addWidget(self.smooth_sb, 0, 1)
        self.grid_layout.addWidget(self.smooth_step_txt, 0, 2)

        self.setLayout(self.grid_layout)


class CompositionGroupBox(QtGui.QGroupBox):
    composition_changed = QtCore.pyqtSignal(dict, float)

    def __init__(self, *args):
        super(CompositionGroupBox, self).__init__("Composition", *args)
        self.create_widgets()

    def create_widgets(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setSpacing(15)
        self.add_element_btn = QtGui.QPushButton("Add")
        self.delete_element_btn = QtGui.QPushButton("Delete")
        self.button_layout.addWidget(self.add_element_btn)
        self.button_layout.addWidget(self.delete_element_btn)

        self.density_layout = QtGui.QHBoxLayout()
        self.density_lbl = QtGui.QLabel("Density:")
        self.density_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.density_txt = QtGui.QLineEdit("2.2")
        self.density_txt.setAlignment(QtCore.Qt.AlignRight)
        self.density_txt.setValidator(QtGui.QDoubleValidator())
        self.density_txt.editingFinished.connect(self.emit_composition_changed_signal)
        self.density_txt.setMaximumWidth(100)
        self.density_layout.addWidget(self.density_lbl)
        self.density_layout.addWidget(self.density_txt)

        self.composition_tw = QtGui.QTableWidget()
        self.composition_tw.setFixedHeight(100)
        self.composition_tw.setColumnCount(2)
        self.composition_tw.horizontalHeader().setVisible(False)
        self.composition_tw.verticalHeader().setVisible(False)
        self.composition_tw.setColumnWidth(0, 80)
        self.composition_tw.setColumnWidth(1, 80)
        self.composition_tw.setItemDelegate(TextDoubleDelegate(self))
        self.composition_tw.cellChanged.connect(self.emit_composition_changed_signal)

        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.composition_tw)
        self.main_layout.addLayout(self.density_layout)

        self.setLayout(self.main_layout)

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
        print self.get_composition()
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


class CalculationGroupBox(QtGui.QGroupBox):
    calculation_parameters_changed = QtCore.pyqtSignal(float, float, float)

    def __init__(self, *args):
        super(CalculationGroupBox, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.q_min_lbl = QtGui.QLabel('Q min:')
        self.q_max_lbl = QtGui.QLabel('Q max:')
        self.r_cutoff_lbl = QtGui.QLabel('r cutoff:')

        self.q_min_txt = QtGui.QLineEdit('0')
        self.q_max_txt = QtGui.QLineEdit('10')
        self.r_cutoff_txt = QtGui.QLineEdit('1')

        self.optimize_btn = QtGui.QPushButton("Optimize")
        self.optimize_r_cutoff_btn = QtGui.QPushButton("Optimize r cutoff")

    def style_widgets(self):
        self.q_min_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setMaximumWidth(80)
        self.q_max_txt.setMaximumWidth(80)
        self.r_cutoff_txt.setMaximumWidth(80)

        self.q_min_txt.setValidator(QtGui.QDoubleValidator())
        self.q_max_txt.setValidator(QtGui.QDoubleValidator())
        self.r_cutoff_txt.setValidator(QtGui.QDoubleValidator())

        self.optimize_btn.setFlat(True)
        self.optimize_r_cutoff_btn.setFlat(True)

    def create_layout(self):
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setSpacing(5)
        self.grid_layout.addWidget(self.q_min_lbl, 0, 0)
        self.grid_layout.addWidget(self.q_min_txt, 0, 1)
        self.grid_layout.addWidget(self.q_max_lbl, 1, 0)
        self.grid_layout.addWidget(self.q_max_txt, 1, 1)
        self.grid_layout.addWidget(self.r_cutoff_lbl, 2, 0)
        self.grid_layout.addWidget(self.r_cutoff_txt, 2, 1)

        self.grid_layout.addWidget(self.optimize_btn, 3, 0, 1, 2)
        self.grid_layout.addWidget(self.optimize_r_cutoff_btn, 4, 0, 1, 2)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.q_max_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.q_min_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.r_cutoff_txt.editingFinished.connect(self.emit_calculation_changed_signal)

    def emit_calculation_changed_signal(self):
        q_min = float(str(self.q_min_txt.text()))
        q_max = float(str(self.q_max_txt.text()))
        r_cutoff = float(str(self.r_cutoff_txt.text()))
        self.calculation_parameters_changed.emit(q_min, q_max, r_cutoff)






# -*- coding: utf-8 -*-

from qtpy import QtCore, QtWidgets
from ..custom import HorizontalLine, FloatLineEdit
from ...model.configuration import NormalizationMethod, SqMethod


class OptionsWidget(QtWidgets.QWidget):
    options_parameters_changed = QtCore.Signal()

    def __init__(self, *args):
        super(OptionsWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.calculation_ranges_gb = QtWidgets.QGroupBox("Ranges")
        self.q_range_lbl = QtWidgets.QLabel('Q:')
        self.q_min_txt = FloatLineEdit('0')
        self.q_max_txt = FloatLineEdit('10')

        self.r_range_lbl = QtWidgets.QLabel('r:')
        self.r_min_txt = FloatLineEdit('0.5')
        self.r_max_txt = FloatLineEdit('10')

        self.modification_fcn_cb = QtWidgets.QCheckBox("Use Modification Function")

        self.normalization_method_gb = QtWidgets.QGroupBox("Normalization")
        self.normalization_method_integral = QtWidgets.QRadioButton("Integral")
        self.normalization_method_integral.setChecked(True)
        self.normalization_method_fit = QtWidgets.QRadioButton("Fit")
        self.normalization_method_fit.setChecked(False)

        self.sq_method_gb = QtWidgets.QGroupBox("S(Q) Method")
        self.sq_method_FZ = QtWidgets.QRadioButton("Faber-Ziman")
        self.sq_method_FZ.setChecked(True)
        self.sq_method_AL = QtWidgets.QRadioButton("Ashcroft-Langreth")
        self.sq_method_AL.setChecked(False)

    def style_widgets(self):
        self.q_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.modification_fcn_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.sq_method_FZ.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.sq_method_AL.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.normalization_method_integral.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.normalization_method_fit.setLayoutDirection(QtCore.Qt.RightToLeft)

    def create_layout(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self._calculation_ranges_layout = QtWidgets.QGridLayout()
        self._calculation_ranges_layout.setSpacing(5)

        self._calculation_ranges_layout.addWidget(self.q_range_lbl, 0, 1)
        self._calculation_ranges_layout.addWidget(self.q_min_txt, 0, 2)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('-'), 0, 3)
        self._calculation_ranges_layout.addWidget(self.q_max_txt, 0, 4)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('A<sup>-1</sup>'), 0, 5)

        self._calculation_ranges_layout.addWidget(self.r_range_lbl, 1, 1)
        self._calculation_ranges_layout.addWidget(self.r_min_txt, 1, 2)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('-'), 1, 3)
        self._calculation_ranges_layout.addWidget(self.r_max_txt, 1, 4)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('A'), 1, 5)
        self.calculation_ranges_gb.setLayout(self._calculation_ranges_layout)
        self.main_layout.addWidget(self.calculation_ranges_gb)

        self.choice_layout = QtWidgets.QHBoxLayout()
        self.choice_layout.setSpacing(5)

        self._normalization_method_gb_layout = QtWidgets.QVBoxLayout()
        self._normalization_method_gb_layout.setSpacing(5)
        self._normalization_method_gb_layout.addWidget(self.normalization_method_integral)
        self._normalization_method_gb_layout.addWidget(self.normalization_method_fit)
        self.normalization_method_gb.setLayout(self._normalization_method_gb_layout)
        self.choice_layout.addWidget(self.normalization_method_gb)

        self._sq_method_gb_layout = QtWidgets.QVBoxLayout()
        self._sq_method_gb_layout.setSpacing(5)
        self._sq_method_gb_layout.addWidget(self.sq_method_FZ)
        self._sq_method_gb_layout.addWidget(self.sq_method_AL)
        self.sq_method_gb.setLayout(self._sq_method_gb_layout)
        self.choice_layout.addWidget(self.sq_method_gb)

        self.main_layout.addLayout(self.choice_layout)
        self.main_layout.addWidget(self.modification_fcn_cb)

        self.setLayout(self.main_layout)

    def create_signals(self):
        self.q_max_txt.editingFinished.connect(self.txt_changed)
        self.q_min_txt.editingFinished.connect(self.txt_changed)
        self.r_min_txt.editingFinished.connect(self.txt_changed)
        self.r_max_txt.editingFinished.connect(self.txt_changed)

        self.modification_fcn_cb.stateChanged.connect(self.options_changed)
        self.sq_method_FZ.toggled.connect(self.options_changed)
        self.sq_method_AL.toggled.connect(self.options_changed)

        self.normalization_method_integral.toggled.connect(self.options_changed)
        self.normalization_method_fit.toggled.connect(self.options_changed)

    def txt_changed(self):
        if self.q_max_txt.isModified() or self.q_min_txt.isModified() or \
                self.r_min_txt.isModified() or self.r_max_txt.isModified():
            self.options_parameters_changed.emit()

            self.q_max_txt.setModified(False)
            self.q_min_txt.setModified(False)
            self.r_min_txt.setModified(False)
            self.r_max_txt.setModified(False)

    def options_changed(self):
        self.options_parameters_changed.emit()

    def get_parameter(self):
        q_min = self.q_min_txt.value()
        q_max = self.q_max_txt.value()
        r_min = self.r_min_txt.value()
        r_max = self.r_max_txt.value()
        return q_min, q_max, r_min, r_max

    def get_normalization_method(self):
        if self.normalization_method_integral.isChecked():
            return NormalizationMethod.Integral
        elif self.normalization_method_fit.isChecked():
            return NormalizationMethod.Fit
        else:
            return None

    def get_sq_method(self):
        if self.sq_method_FZ.isChecked():
            return SqMethod.FZ
        elif self.sq_method_AL.isChecked():
            return SqMethod.AL
        else:
            return None

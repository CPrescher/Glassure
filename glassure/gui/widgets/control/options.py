# -*- coding: utf-8 -*-

from qtpy import QtCore, QtWidgets
from ..custom import HorizontalLine, FloatLineEdit, DragSlider
import numpy as np
from ...model.configuration import NormalizationMethod, SqMethod, TransformConfiguration, FourierTransformMethod


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
        self.q_max_slider = DragSlider()

        self.r_range_lbl = QtWidgets.QLabel('r:')
        self.r_min_txt = FloatLineEdit('0.5')
        self.r_max_txt = FloatLineEdit('10')

        self.modification_fcn_cb = QtWidgets.QCheckBox("Use Modification Function")
        self.fft_cb = QtWidgets.QCheckBox("Use FFT")
        self.fft_cb.setToolTip(
            "Use FFT for Fourier Transform. If not checked, the Fourier integral is solver numerically.")

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

        self.sq_method_FZ.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.sq_method_AL.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.normalization_method_integral.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.normalization_method_fit.setLayoutDirection(QtCore.Qt.RightToLeft)

        self.modification_fcn_cb.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.fft_cb.setLayoutDirection(QtCore.Qt.RightToLeft)

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

        self._calculation_ranges_layout.addWidget(self.q_max_slider, 1, 4, 1, 1)

        self._calculation_ranges_layout.addWidget(self.r_range_lbl, 2, 1)
        self._calculation_ranges_layout.addWidget(self.r_min_txt, 2, 2)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('-'), 2, 3)
        self._calculation_ranges_layout.addWidget(self.r_max_txt, 2, 4)
        self._calculation_ranges_layout.addWidget(QtWidgets.QLabel('A'), 2, 5)
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
        self.main_layout.addWidget(self.fft_cb)

        self.setLayout(self.main_layout)

    def create_signals(self):
        self.q_max_txt.editingFinished.connect(self.txt_changed)
        self.q_min_txt.editingFinished.connect(self.txt_changed)
        self.q_max_slider.dragChanged.connect(self.q_max_slider_changed)
        self.r_min_txt.editingFinished.connect(self.txt_changed)
        self.r_max_txt.editingFinished.connect(self.txt_changed)

        self.modification_fcn_cb.stateChanged.connect(self.options_changed)
        self.fft_cb.stateChanged.connect(self.options_changed)
        self.sq_method_FZ.toggled.connect(self.options_changed)
        self.normalization_method_integral.toggled.connect(self.options_changed)

    def txt_changed(self):
        if self.q_max_txt.isModified() or self.q_min_txt.isModified() or \
                self.r_min_txt.isModified() or self.r_max_txt.isModified():
            self.options_parameters_changed.emit()

            self.q_max_txt.setModified(False)
            self.q_min_txt.setModified(False)
            self.r_min_txt.setModified(False)
            self.r_max_txt.setModified(False)

    def q_max_slider_changed(self):
        q_max = float(self.q_max_txt.text())
        factor = np.tan(self.q_max_slider.value() / 75) / 150 + 1
        self.q_max_txt.setText(f"{factor * q_max:.2f}")
        self.options_changed()

    def options_changed(self):
        self.options_parameters_changed.emit()

    def get_ranges(self):
        q_min = self.q_min_txt.value()
        q_max = self.q_max_txt.value()
        r_min = self.r_min_txt.value()
        r_max = self.r_max_txt.value()
        return q_min, q_max, r_min, r_max

    def get_normalization_method(self):
        if self.normalization_method_integral.isChecked():
            return NormalizationMethod.INTEGRAL
        elif self.normalization_method_fit.isChecked():
            return NormalizationMethod.FIT
        else:
            return None

    def get_sq_method(self):
        if self.sq_method_FZ.isChecked():
            return SqMethod.FZ
        elif self.sq_method_AL.isChecked():
            return SqMethod.AL
        else:
            return None

    def get_fourier_transform_method(self):
        if self.fft_cb.isChecked():
            return FourierTransformMethod.FFT
        else:
            return FourierTransformMethod.INTEGRAL

    def set_fourier_transform_method(self, method):
        if method == 'fft':
            self.fft_cb.setChecked(True)
        else:
            self.fft_cb.setChecked(False)

    def get_transform_configuration(self) -> TransformConfiguration:
        config = TransformConfiguration()
        config.q_min, config.q_max, config.r_min, config.r_max = self.get_ranges()
        config.normalization_method = self.get_normalization_method()
        config.sq_method = self.get_sq_method()
        config.use_modification_fcn = self.modification_fcn_cb.isChecked()
        config.fourier_transform_method = self.get_fourier_transform_method()

        return config

    def update_transform_configuration(self, config: TransformConfiguration):
        self.blockSignals(True)
        self.q_min_txt.setText(f"{config.q_min:.2f}")
        self.q_max_txt.setText(f"{config.q_max:.2f}")
        self.r_min_txt.setText(f"{config.r_min:.2f}")
        self.r_max_txt.setText(f"{config.r_max:.2f}")

        self.modification_fcn_cb.blockSignals(True)
        self.modification_fcn_cb.setChecked(config.use_modification_fcn)
        self.modification_fcn_cb.blockSignals(False)

        if config.normalization_method == NormalizationMethod.INTEGRAL:
            self.normalization_method_integral.setChecked(True)
        elif config.normalization_method == NormalizationMethod.FIT:
            self.normalization_method_fit.setChecked(True)
        if config.sq_method == SqMethod.FZ:
            self.sq_method_FZ.setChecked(True)
        elif config.sq_method == SqMethod.AL:
            self.sq_method_AL.setChecked(True)

        self.set_fourier_transform_method(config.fourier_transform_method)
        self.blockSignals(False)

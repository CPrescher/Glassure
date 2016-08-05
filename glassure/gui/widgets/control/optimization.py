# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal

from ..custom import NumberTextField, LabelAlignRight, HorizontalLine


class OptimizationWidget(QtGui.QWidget):
    optimization_parameters_changed = Signal()

    def __init__(self, *args):
        super(OptimizationWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

        self.param_widget.setVisible(False)
        self.activate_cb.setChecked(False)

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")

        self.r_cutoff_lbl = LabelAlignRight('r cutoff:')
        self.r_cutoff_txt = NumberTextField('1.4')

        self.optimize_iterations_lbl = LabelAlignRight("Iterations:")
        self.optimize_iterations_txt = NumberTextField('5')

        self.attenuation_factor_lbl = LabelAlignRight("Attenuation:")
        self.attenuation_factor_sb = QtGui.QSpinBox()

        self.plot_progress_cb = QtGui.QCheckBox('plot progress')

    def style_widgets(self):

        self.r_cutoff_txt.setMaximumWidth(80)
        self.optimize_iterations_txt.setMaximumWidth(80)

        self.r_cutoff_txt.setValidator(QtGui.QDoubleValidator())
        self.optimize_iterations_txt.setValidator(QtGui.QIntValidator())

        self.attenuation_factor_sb.setRange(1, 1000)
        self.attenuation_factor_sb.setSingleStep(1)
        self.attenuation_factor_sb.setValue(1)
        self.attenuation_factor_sb.setAlignment(QtCore.Qt.AlignRight)

    def create_layout(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.main_layout.addWidget(self.activate_cb)
        self.main_layout.addWidget(HorizontalLine())

        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.r_cutoff_lbl, 1, 0)
        self.grid_layout.addWidget(self.r_cutoff_txt, 1, 1)
        self.grid_layout.addWidget(QtGui.QLabel('A'), 1, 2)

        self.grid_layout.addWidget(self.optimize_iterations_lbl, 4, 0)
        self.grid_layout.addWidget(self.optimize_iterations_txt, 4, 1)

        self.grid_layout.addWidget(self.attenuation_factor_lbl, 5, 0)
        self.grid_layout.addWidget(self.attenuation_factor_sb, 5, 1)

        self.grid_layout.addWidget(self.plot_progress_cb, 6, 1, 1, 2)

        self.param_widget = QtGui.QWidget()
        self.param_widget.setLayout(self.grid_layout)

        self.main_layout.addWidget(self.param_widget)

        self.setLayout(self.main_layout)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.param_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.optimization_parameters_changed.emit)

        self.r_cutoff_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.optimize_iterations_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.attenuation_factor_sb.valueChanged.connect(self.optimization_parameters_changed.emit)


    def emit_calculation_changed_signal(self):
        if self.r_cutoff_txt.isModified():
            self.optimization_parameters_changed.emit()
            self.r_cutoff_txt.setModified(False)
        elif self.optimize_iterations_txt.isModified():
            self.optimization_parameters_changed.emit()
            self.optimize_iterations_txt.setModified(False)

    def get_parameter(self):
        activate = self.activate_cb.isChecked()
        r_cutoff = float(str(self.r_cutoff_txt.text()))
        iterations = int(str(self.optimize_iterations_txt.text()))
        attenuation = int(self.attenuation_factor_sb.value())
        return activate, r_cutoff, iterations, attenuation

    def set_parameter(self, r_cutoff, iterations, attenuation):
        self.blockSignals(True)
        self.r_cutoff_txt.setText(str(r_cutoff))
        self.optimize_iterations_txt.setText(str(int(iterations)))
        self.attenuation_factor_sb.setValue(attenuation)
        self.blockSignals(False)

# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal


class OptimizationWidget(QtGui.QWidget):
    calculation_parameters_changed = Signal()

    def __init__(self, *args):
        super(OptimizationWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.r_cutoff_lbl = QtGui.QLabel('r cutoff:')
        self.r_cutoff_txt = QtGui.QLineEdit('1.4')

        self.optimize_btn = QtGui.QPushButton("Optimize")
        self.optimize_iterations_lbl = QtGui.QLabel("Iterations:")
        self.optimize_iterations_txt = QtGui.QLineEdit('5')

        self.attenuation_factor_lbl = QtGui.QLabel("Attenuation:")
        self.attenuation_factor_sb = QtGui.QSpinBox()

    def style_widgets(self):
        self.r_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.optimize_iterations_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.r_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.optimize_iterations_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.r_cutoff_txt.setMaximumWidth(80)
        self.optimize_iterations_txt.setMaximumWidth(80)

        self.r_cutoff_txt.setValidator(QtGui.QDoubleValidator())
        self.optimize_iterations_txt.setValidator(QtGui.QIntValidator())

        self.attenuation_factor_sb.setRange(1, 1000)
        self.attenuation_factor_sb.setSingleStep(1)
        self.attenuation_factor_sb.setValue(1)
        self.attenuation_factor_sb.setAlignment(QtCore.Qt.AlignRight)

        self.optimize_btn.setFlat(True)

    def create_layout(self):
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

        self.grid_layout.addWidget(self.optimize_btn, 6, 0, 1, 5)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.r_cutoff_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.optimize_iterations_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.attenuation_factor_sb.valueChanged.connect(self.calculation_parameters_changed.emit)

    def emit_calculation_changed_signal(self):
        if self.r_cutoff_txt.isModified():
            self.calculation_parameters_changed.emit()
            self.r_cutoff_txt.setModified(False)
        elif self.optimize_iterations_txt.isModified():
            self.calculation_parameters_changed.emit()
            self.optimize_iterations_txt.setModified(False)

    def get_parameter(self):
        r_cutoff = float(str(self.r_cutoff_txt.text()))
        iterations = int(str(self.optimize_iterations_txt.text()))
        attenuation = int(self.attenuation_factor_sb.value())
        return r_cutoff, iterations, attenuation

    def set_parameter(self, r_cutoff, iterations, attenuation):
        self.blockSignals(True)
        self.r_cutoff_txt.setText(str(r_cutoff))
        self.optimize_iterations_txt.setText(str(int(iterations)))
        self.attenuation_factor_sb.setValue(attenuation)
        self.blockSignals(False)

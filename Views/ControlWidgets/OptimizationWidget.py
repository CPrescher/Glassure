# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtCore, QtGui

class OptimizationWidget(QtGui.QWidget):
    calculation_parameters_changed = QtCore.pyqtSignal(float, float, float)

    def __init__(self, *args):
        super(OptimizationWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.q_range_lbl = QtGui.QLabel('Q range:')
        self.r_cutoff_lbl = QtGui.QLabel('r cutoff:')

        self.q_min_txt = QtGui.QLineEdit('0')
        self.q_max_txt = QtGui.QLineEdit('10')
        self.r_cutoff_txt = QtGui.QLineEdit('1')

        self.r_range_lbl = QtGui.QLabel('r range:')
        self.r_min_txt = QtGui.QLineEdit('0.5')
        self.r_max_txt = QtGui.QLineEdit('10')

        self.optimize_btn = QtGui.QPushButton("Optimize")
        self.optimize_density_btn = QtGui.QPushButton("Optimize Density")
        self.optimize_iterations_lbl = QtGui.QLabel("Iterations:")
        self.optimize_iterations_txt = QtGui.QLineEdit('50')

    def style_widgets(self):
        self.q_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.optimize_iterations_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.r_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.optimize_iterations_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setMaximumWidth(80)
        self.q_max_txt.setMaximumWidth(80)
        self.r_cutoff_txt.setMaximumWidth(80)
        self.optimize_iterations_txt.setMaximumWidth(80)

        self.q_min_txt.setValidator(QtGui.QDoubleValidator())
        self.q_max_txt.setValidator(QtGui.QDoubleValidator())
        self.r_min_txt.setValidator(QtGui.QDoubleValidator())
        self.r_max_txt.setValidator(QtGui.QDoubleValidator())
        self.r_cutoff_txt.setValidator(QtGui.QDoubleValidator())
        self.optimize_iterations_txt.setValidator(QtGui.QIntValidator())

        self.optimize_btn.setFlat(True)
        self.optimize_density_btn.setFlat(True)

    def create_layout(self):
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.q_range_lbl, 0, 0)
        self.grid_layout.addWidget(self.q_min_txt, 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 0, 2)
        self.grid_layout.addWidget(self.q_max_txt, 0, 3)
        self.grid_layout.addWidget(QtGui.QLabel('A<sup>-1</sup>'), 0, 4)

        self.grid_layout.addWidget(self.r_cutoff_lbl, 1, 0)
        self.grid_layout.addWidget(self.r_cutoff_txt, 1, 1)
        self.grid_layout.addWidget(QtGui.QLabel('A'), 1, 2)

        self.grid_layout.addWidget(self.r_range_lbl, 2, 0)
        self.grid_layout.addWidget(self.r_min_txt, 2, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 2, 2)
        self.grid_layout.addWidget(self.r_max_txt, 2, 3)
        self.grid_layout.addWidget(QtGui.QLabel('A'), 2, 4)

        self.grid_layout.addWidget(horizontal_line(), 3, 0, 1, 5)
        self.grid_layout.addWidget(self.optimize_iterations_lbl, 4, 0)
        self.grid_layout.addWidget(self.optimize_iterations_txt, 4, 1)
        self.grid_layout.addWidget(self.optimize_btn, 5, 0, 1, 5)
        self.grid_layout.addWidget(self.optimize_density_btn, 6, 0, 1, 5)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.q_max_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.q_min_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.r_cutoff_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.r_min_txt.editingFinished.connect(self.emit_calculation_changed_signal)
        self.r_max_txt.editingFinished.connect(self.emit_calculation_changed_signal)

    def emit_calculation_changed_signal(self):
        if self.q_max_txt.isModified() or self.q_min_txt.isModified() or self.r_cutoff_txt.isModified() or \
                self.r_min_txt.isModified() or self.r_max_txt.isModified():
            q_min = float(str(self.q_min_txt.text()))
            q_max = float(str(self.q_max_txt.text()))
            r_cutoff = float(str(self.r_cutoff_txt.text()))
            self.calculation_parameters_changed.emit(q_min, q_max, r_cutoff)

            self.q_max_txt.setModified(False)
            self.q_min_txt.setModified(False)
            self.r_cutoff_txt.setModified(False)
            self.r_min_txt.setModified(False)
            self.r_max_txt.setModified(False)

    def get_parameter(self):
        q_min = float(str(self.q_min_txt.text()))
        q_max = float(str(self.q_max_txt.text()))
        r_cutoff = float(str(self.r_cutoff_txt.text()))
        r_min = float(str(self.r_min_txt.text()))
        r_max = float(str(self.r_max_txt.text()))
        return q_min, q_max, r_cutoff, r_min, r_max


def horizontal_line():
    frame = QtGui.QFrame()
    frame.setFrameShape(QtGui.QFrame.HLine)
    frame.setStyleSheet("border: 2px solid #CCC;")
    frame.setFrameShadow(QtGui.QFrame.Sunken)
    return frame
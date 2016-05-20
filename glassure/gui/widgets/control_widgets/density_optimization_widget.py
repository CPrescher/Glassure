# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal


class DensityOptimizationWidget(QtGui.QWidget):
    calculation_parameters_changed = Signal(float)

    def __init__(self, *args):
        super(DensityOptimizationWidget, self).__init__(*args)
        self.create_widgets()
        self.style_widgets()
        self.create_layout()

    def create_widgets(self):
        self.density_range_lbl = QtGui.QLabel('Density range:')
        self.density_min_txt = QtGui.QLineEdit('1')
        self.density_max_txt = QtGui.QLineEdit('10')

        self.bkg_range_lbl = QtGui.QLabel('Bkg range:')
        self.bkg_min_txt = QtGui.QLineEdit('0.1')
        self.bkg_max_txt = QtGui.QLineEdit('2')

        self.optimize_btn = QtGui.QPushButton("Optimize")
        self.optimize_iterations_lbl = QtGui.QLabel("Iterations:")
        self.optimize_iterations_txt = QtGui.QLineEdit('5')

        self.optimization_output_txt = QtGui.QTextEdit()
        self.optimization_output_txt.setReadOnly(True)

    def style_widgets(self):
        self.density_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.bkg_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.optimize_iterations_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.density_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.density_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.bkg_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.bkg_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.optimize_iterations_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.density_min_txt.setValidator(QtGui.QDoubleValidator())
        self.density_max_txt.setValidator(QtGui.QDoubleValidator())
        self.bkg_min_txt.setValidator(QtGui.QDoubleValidator())
        self.bkg_max_txt.setValidator(QtGui.QDoubleValidator())

        self.optimize_iterations_txt.setMaximumWidth(80)
        self.optimize_iterations_txt.setValidator(QtGui.QIntValidator())

        self.optimize_btn.setFlat(True)

    def create_layout(self):
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.density_range_lbl, 0, 0)
        self.grid_layout.addWidget(self.density_min_txt, 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 0, 2)
        self.grid_layout.addWidget(self.density_max_txt, 0, 3)
        self.grid_layout.addWidget(QtGui.QLabel("g/cm^3"), 0, 4)

        self.grid_layout.addWidget(self.bkg_range_lbl, 1, 0)
        self.grid_layout.addWidget(self.bkg_min_txt, 1, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 1, 2)
        self.grid_layout.addWidget(self.bkg_max_txt, 1, 3)

        self.grid_layout.addWidget(self.optimize_iterations_lbl, 2, 0)
        self.grid_layout.addWidget(self.optimize_iterations_txt, 2, 1)

        self.grid_layout.addWidget(self.optimize_btn, 3, 0, 1, 5)
        self.grid_layout.addWidget(self.optimization_output_txt, 4, 0, 1, 5)

        self.setLayout(self.grid_layout)

    def get_parameter(self):
        density_min = float(str(self.density_min_txt.text()))
        density_max = float(str(self.density_max_txt.text()))
        bkg_min = float(str(self.bkg_min_txt.text()))
        bkg_max = float(str(self.bkg_max_txt.text()))
        iterations = int(str(self.optimize_iterations_txt.text()))
        return density_min, density_max, bkg_min, bkg_max, iterations

# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets
from ..custom import HorizontalLine, FloatLineEdit, IntegerLineEdit


class DensityOptimizationWidget(QtWidgets.QWidget):
    calculation_parameters_changed = QtCore.Signal(float)

    def __init__(self, *args):
        super(DensityOptimizationWidget, self).__init__(*args)
        self.create_widgets()
        self.style_widgets()
        self.create_layout()

    def create_widgets(self):
        self.density_range_lbl = QtWidgets.QLabel('Density range:')
        self.density_min_txt = FloatLineEdit('1')
        self.density_max_txt = FloatLineEdit('10')

        self.bkg_range_lbl = QtWidgets.QLabel("Bkg range:")
        self.bkg_min_txt = FloatLineEdit('0.1')
        self.bkg_max_txt = FloatLineEdit('2')

        self.optimize_btn = QtWidgets.QPushButton("Optimize")
        self.optimize_iterations_lbl = QtWidgets.QLabel("Iterations:")

        self.optimize_iterations_txt = IntegerLineEdit("5")
        self.optimization_output_txt = QtWidgets.QTextEdit()
        self.optimization_output_txt.setReadOnly(True)

    def style_widgets(self):
        center_right = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        self.density_range_lbl.setAlignment(center_right)
        self.bkg_range_lbl.setAlignment(center_right)
        self.optimize_iterations_lbl.setAlignment(center_right)

        self.optimize_iterations_txt.setMaximumWidth(80)

        self.optimize_btn.setFlat(True)

    def create_layout(self):
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.density_range_lbl, 0, 0)
        self.grid_layout.addWidget(self.density_min_txt, 0, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel('-'), 0, 2)
        self.grid_layout.addWidget(self.density_max_txt, 0, 3)
        self.grid_layout.addWidget(QtWidgets.QLabel("g/cm^3"), 0, 4)

        self.grid_layout.addWidget(self.bkg_range_lbl, 1, 0)
        self.grid_layout.addWidget(self.bkg_min_txt, 1, 1)
        self.grid_layout.addWidget(QtWidgets.QLabel('-'), 1, 2)
        self.grid_layout.addWidget(self.bkg_max_txt, 1, 3)

        self.grid_layout.addWidget(self.optimize_iterations_lbl, 2, 0)
        self.grid_layout.addWidget(self.optimize_iterations_txt, 2, 1)

        self.grid_layout.addWidget(self.optimize_btn, 3, 0, 1, 5)
        self.grid_layout.addWidget(self.optimization_output_txt, 4, 0, 1, 5)

        self.setLayout(self.grid_layout)

    def get_parameter(self):
        density_min = self.density_min_txt.value()
        density_max = self.density_max_txt.value()
        bkg_min = self.bkg_min_txt.value()
        bkg_max = self.bkg_max_txt.value()
        iterations = self.optimize_iterations_txt.value()
        return density_min, density_max, bkg_min, bkg_max, iterations

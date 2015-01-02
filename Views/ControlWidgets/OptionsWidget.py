# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'


from PyQt4 import QtCore, QtGui
from CustomWidgets import HorizontalLine

class OptionsWidget(QtGui.QWidget):
    options_parameters_changed = QtCore.pyqtSignal()

    def __init__(self, *args):
        super(OptionsWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.q_range_lbl = QtGui.QLabel('Q range:')
        self.q_min_txt = QtGui.QLineEdit('0')
        self.q_max_txt = QtGui.QLineEdit('10')

        self.r_range_lbl = QtGui.QLabel('r range:')
        self.r_min_txt = QtGui.QLineEdit('0.5')
        self.r_max_txt = QtGui.QLineEdit('10')

        self.modification_fcn_cb = QtGui.QCheckBox("Use Modification Function")
        self.linear_interpolation_cb = QtGui.QCheckBox("Linear Interpolation")

    def style_widgets(self):
        self.q_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.r_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.r_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.q_min_txt.setMaximumWidth(80)
        self.q_max_txt.setMaximumWidth(80)

        self.q_min_txt.setValidator(QtGui.QDoubleValidator())
        self.q_max_txt.setValidator(QtGui.QDoubleValidator())
        self.r_min_txt.setValidator(QtGui.QDoubleValidator())
        self.r_max_txt.setValidator(QtGui.QDoubleValidator())

    def create_layout(self):
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.q_range_lbl, 0, 0)
        self.grid_layout.addWidget(self.q_min_txt, 0, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 0, 2)
        self.grid_layout.addWidget(self.q_max_txt, 0, 3)
        self.grid_layout.addWidget(QtGui.QLabel('A<sup>-1</sup>'), 0, 4)

        self.grid_layout.addWidget(self.r_range_lbl, 1, 0)
        self.grid_layout.addWidget(self.r_min_txt, 1, 1)
        self.grid_layout.addWidget(QtGui.QLabel('-'), 1, 2)
        self.grid_layout.addWidget(self.r_max_txt, 1, 3)
        self.grid_layout.addWidget(QtGui.QLabel('A'), 1, 4)

        self.grid_layout.addWidget(HorizontalLine(), 2, 0, 1, 5)

        self.grid_layout.addWidget(self.modification_fcn_cb, 3, 1, 1, 4)
        self.grid_layout.addWidget(self.linear_interpolation_cb, 4, 1, 1, 4)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.q_max_txt.editingFinished.connect(self.txt_changed)
        self.q_min_txt.editingFinished.connect(self.txt_changed)
        self.r_min_txt.editingFinished.connect(self.txt_changed)
        self.r_max_txt.editingFinished.connect(self.txt_changed)

        self.modification_fcn_cb.stateChanged.connect(self.options_parameters_changed.emit)
        self.linear_interpolation_cb.stateChanged.connect(self.options_parameters_changed.emit)

    def txt_changed(self):
        if self.q_max_txt.isModified() or self.q_min_txt.isModified() or \
                self.r_min_txt.isModified() or self.r_max_txt.isModified():
            self.options_parameters_changed.emit()

            self.q_max_txt.setModified(False)
            self.q_min_txt.setModified(False)
            self.r_min_txt.setModified(False)
            self.r_max_txt.setModified(False)

    def get_parameter(self):
        q_min = float(str(self.q_min_txt.text()))
        q_max = float(str(self.q_max_txt.text()))
        r_min = float(str(self.r_min_txt.text()))
        r_max = float(str(self.r_max_txt.text()))
        return q_min, q_max, r_min, r_max

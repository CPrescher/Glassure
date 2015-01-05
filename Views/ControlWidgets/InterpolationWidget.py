# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'


from PyQt4 import QtCore, QtGui
from CustomWidgets import HorizontalLine

class InterpolationWidget(QtGui.QWidget):
    interpolation_parameters_changed = QtCore.pyqtSignal()

    def __init__(self, *args):
        super(InterpolationWidget, self).__init__(*args)

        self.create_widgets()
        self.create_layout()
        self.style_widgets()
        self.create_signals()

        self.disable_rb_widgets()
        self.disable_spline_widgets()

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")
        self.linear_interpolation_rb = QtGui.QRadioButton("Linear")
        self.linear_interpolation_rb.setChecked(True)
        self.spline_interpolation_rb = QtGui.QRadioButton("Spline")

        self.spline_interpolation_cutoff_lbl = QtGui.QLabel('Cutoff:')
        self.spline_interpolation_cutoff_txt = QtGui.QLineEdit('0.5')

        self.spline_interpolation_fit_range_lbl = QtGui.QLabel('Fit range:')
        self.spline_interpolation_fit_range_min_txt = QtGui.QLineEdit('1')
        self.spline_interpolation_fit_range_max_txt = QtGui.QLineEdit('1.5')

    def style_widgets(self):
        self.spline_interpolation_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_interpolation_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.spline_interpolation_fit_range_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_interpolation_fit_range_min_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_interpolation_fit_range_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def create_layout(self):
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0,0,0,0)
        self.vertical_layout.setSpacing(5)

        self.vertical_layout.addWidget(self.activate_cb)
        self.vertical_layout.addWidget(HorizontalLine())

        self.rb_horizontal_layout = QtGui.QHBoxLayout()
        self.rb_horizontal_layout.setContentsMargins(0,0,0,0)
        self.rb_horizontal_layout.setSpacing(5)
        self.rb_horizontal_layout.addSpacing(10)

        self.rb_widget = QtGui.QWidget(self)

        self.rb_ver_layout = QtGui.QVBoxLayout()
        self.rb_ver_layout.setContentsMargins(0,0,0,0)
        self.rb_ver_layout.setSpacing(5)

        self.rb_ver_layout.addWidget(self.linear_interpolation_rb)
        self.rb_ver_layout.addWidget(self.spline_interpolation_rb)

        self.spline_interpolation_widget = QtGui.QWidget(self)
        self.spline_interpolation_parameter_layout = QtGui.QGridLayout()
        self.spline_interpolation_parameter_layout.setContentsMargins(0,0,0,0)
        self.spline_interpolation_parameter_layout.setSpacing(5)

        self.spline_interpolation_parameter_layout.addItem(QtGui.QSpacerItem(10,10), 0, 0)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_cutoff_lbl, 0, 1)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_cutoff_txt, 0, 2)

        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_fit_range_lbl, 1, 1)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_fit_range_min_txt, 1, 2)
        self.spline_interpolation_parameter_layout.addWidget(QtGui.QLabel('-'), 1, 3)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_fit_range_max_txt, 1, 4)
        self.spline_interpolation_parameter_layout.addWidget(QtGui.QLabel('Q'), 1, 5)

        self.spline_interpolation_widget.setLayout(self.spline_interpolation_parameter_layout)
        self.rb_ver_layout.addWidget(self.spline_interpolation_widget)
        self.rb_horizontal_layout.addLayout(self.rb_ver_layout)

        self.rb_widget.setLayout(self.rb_horizontal_layout)
        self.vertical_layout.addWidget(self.rb_widget)
        self.setLayout(self.vertical_layout)

    def disable_rb_widgets(self):
        self.rb_widget.setEnabled(False)

    def enable_rb_widgets(self):
        self.rb_widget.setEnabled(True)

    def disable_spline_widgets(self):
        self.spline_interpolation_widget.setEnabled(False)

    def enable_spline_widgets(self):
        self.spline_interpolation_widget.setEnabled(True)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.rb_widget.setEnabled)
        self.activate_cb.stateChanged.connect(self.interpolation_parameters_changed.emit)

        self.linear_interpolation_rb.toggled.connect(self.interpolation_parameters_changed.emit)
        self.linear_interpolation_rb.toggled.connect(self.update_visibility)

        self.spline_interpolation_cutoff_txt.editingFinished.connect(self.txt_changed)
        self.spline_interpolation_fit_range_max_txt.editingFinished.connect(self.txt_changed)
        self.spline_interpolation_fit_range_min_txt.editingFinished.connect(self.txt_changed)

    def update_visibility(self):
        if self.spline_interpolation_rb.isChecked():
            self.enable_spline_widgets()
        else:
            self.disable_spline_widgets()

    def txt_changed(self):
        if self.spline_interpolation_cutoff_txt.isModified() and \
            self.spline_interpolation_fit_range_min_txt.isModified() and \
            self.spline_interpolation_fit_range_max_txt.isModified():

            self.interpolation_parameters_changed.emit()

            self.spline_interpolation_cutoff_txt.setModified(False)
            self.spline_interpolation_fit_range_max_txt.setModified(False)
            self.spline_interpolation_fit_range_min_txt.setModified(False)

    def get_interpolation_method(self):
        if not self.activate_cb.isChecked():
            return None
        elif self.linear_interpolation_rb.isChecked():
            return "linear"
        elif self.spline_interpolation_rb.isChecked():
            return "spline"
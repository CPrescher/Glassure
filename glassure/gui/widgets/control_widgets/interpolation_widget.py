# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal

from ..custom_widgets import HorizontalLine


class InterpolationWidget(QtGui.QWidget):
    interpolation_parameters_changed = Signal()

    def __init__(self, *args):
        super(InterpolationWidget, self).__init__(*args)

        self.create_widgets()
        self.create_layout()
        self.style_widgets()
        self.create_signals()

        self.disable_spline_widgets()
        self.rb_widget.setVisible(False)

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")

        self.linear_interpolation_rb = QtGui.QRadioButton("Linear")
        self.linear_interpolation_rb.setChecked(True)
        self.linear_intercept_lbl = QtGui.QLabel("Intercept:")
        self.linear_intercept_txt = QtGui.QLineEdit("1")

        self.poly_interpolation_rb = QtGui.QRadioButton("Polynomial")
        self.poly_interpolation_q_max_lbl = QtGui.QLabel("Q Max:")
        self.poly_interpolation_q_max_txt = QtGui.QLineEdit("2")
        self.poly_interpolation_replace_cb = QtGui.QCheckBox("replace")

        self.spline_interpolation_rb = QtGui.QRadioButton("Spline")
        self.spline_interpolation_cutoff_lbl = QtGui.QLabel('Cutoff:')
        self.spline_interpolation_cutoff_txt = QtGui.QLineEdit('0.5')
        self.spline_interpolation_q_max_lbl = QtGui.QLabel('Q Max:')
        self.spline_interpolation_q_max_txt = QtGui.QLineEdit('1.5')

    def style_widgets(self):

        self.poly_interpolation_q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.poly_interpolation_q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.poly_interpolation_q_max_txt.setMaximumWidth(50)

        self.spline_interpolation_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_interpolation_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.spline_interpolation_q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_interpolation_q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.spline_interpolation_cutoff_txt.setValidator(QtGui.QDoubleValidator())
        self.spline_interpolation_q_max_txt.setValidator(QtGui.QDoubleValidator())

        self.spline_interpolation_cutoff_txt.setMaximumWidth(50)
        self.spline_interpolation_q_max_txt.setMaximumWidth(50)

    def create_layout(self):
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.vertical_layout.setSpacing(5)

        self.vertical_layout.addWidget(self.activate_cb)
        self.vertical_layout.addWidget(HorizontalLine())

        self.rb_horizontal_layout = QtGui.QHBoxLayout()
        self.rb_horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.rb_horizontal_layout.setSpacing(5)
        self.rb_horizontal_layout.addSpacing(10)

        self.rb_widget = QtGui.QWidget(self)

        self.rb_ver_layout = QtGui.QVBoxLayout()
        self.rb_ver_layout.setContentsMargins(0, 0, 0, 0)
        self.rb_ver_layout.setSpacing(5)

        self.rb_ver_layout.addWidget(self.linear_interpolation_rb)

        self.rb_ver_layout.addWidget(self.poly_interpolation_rb)
        self.poly_interpolation_widget = QtGui.QWidget(self)
        self.poly_interpolation_layout = QtGui.QGridLayout()
        self.poly_interpolation_layout.setContentsMargins(0, 0, 0, 0)
        self.poly_interpolation_layout.setSpacing(5)

        self.poly_interpolation_layout.addItem(QtGui.QSpacerItem(10, 10), 0, 0)
        self.poly_interpolation_layout.addWidget(self.poly_interpolation_q_max_lbl, 0, 1)
        self.poly_interpolation_layout.addWidget(self.poly_interpolation_q_max_txt, 0, 2)
        self.poly_interpolation_layout.addWidget(self.poly_interpolation_replace_cb, 1, 2)
        self.poly_interpolation_layout.addWidget(QtGui.QLabel('A-1'), 0, 3)

        self.poly_interpolation_widget.setLayout(self.poly_interpolation_layout)

        self.rb_ver_layout.addWidget(self.poly_interpolation_widget)
        self.rb_ver_layout.addWidget(self.spline_interpolation_rb)

        self.spline_interpolation_widget = QtGui.QWidget(self)
        self.spline_interpolation_parameter_layout = QtGui.QGridLayout()
        self.spline_interpolation_parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.spline_interpolation_parameter_layout.setSpacing(5)

        self.spline_interpolation_parameter_layout.addItem(QtGui.QSpacerItem(10, 10), 0, 0)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_cutoff_lbl, 0, 1)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_cutoff_txt, 0, 2)

        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_q_max_lbl, 1, 1)
        self.spline_interpolation_parameter_layout.addWidget(self.spline_interpolation_q_max_txt, 1, 2)
        self.spline_interpolation_parameter_layout.addWidget(QtGui.QLabel('A'), 1, 3)

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
        self.activate_cb.stateChanged.connect(self.rb_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.interpolation_parameters_changed.emit)

        self.linear_interpolation_rb.toggled.connect(self.interpolation_parameters_changed.emit)
        self.linear_interpolation_rb.toggled.connect(self.update_visibility)

        self.spline_interpolation_cutoff_txt.editingFinished.connect(self.txt_changed)
        self.spline_interpolation_q_max_txt.editingFinished.connect(self.txt_changed)

    def update_visibility(self):
        if self.spline_interpolation_rb.isChecked():
            self.enable_spline_widgets()
        else:
            self.disable_spline_widgets()

    def txt_changed(self):
        if self.spline_interpolation_cutoff_txt.isModified() or \
                self.spline_interpolation_q_max_txt.isModified():
            self.interpolation_parameters_changed.emit()

            self.spline_interpolation_cutoff_txt.setModified(False)
            self.spline_interpolation_q_max_txt.setModified(False)

    def get_interpolation_method(self):
        if not self.activate_cb.isChecked():
            return None
        elif self.linear_interpolation_rb.isChecked():
            return "linear"
        elif self.spline_interpolation_rb.isChecked():
            return "spline"

    def get_interpolation_parameters(self):
        return {'cutoff': float(str(self.spline_interpolation_cutoff_txt.text())),
                'q_max': float(str(self.spline_interpolation_q_max_txt.text()))}

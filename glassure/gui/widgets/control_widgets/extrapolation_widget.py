# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal

from ..custom_widgets import HorizontalLine


class ExtrapolationWidget(QtGui.QWidget):
    extrapolation_parameters_changed = Signal()

    def __init__(self, *args):
        super(ExtrapolationWidget, self).__init__(*args)

        self.create_widgets()
        self.create_layout()
        self.style_widgets()
        self.create_signals()

        self.disable_spline_widgets()
        self.rb_widget.setVisible(False)

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")

        self.step_extrapolation_rb = QtGui.QRadioButton('Step')
        self.step_extrapolation_rb.setChecked(True)

        self.linear_extrapolation_rb = QtGui.QRadioButton("Linear")

        self.poly_extrapolation_rb = QtGui.QRadioButton("Polynomial")
        self.poly_extrapolation_q_max_lbl = QtGui.QLabel("Q Max:")
        self.poly_extrapolation_q_max_txt = QtGui.QLineEdit("2")
        self.poly_extrapolation_replace_cb = QtGui.QCheckBox("replace")

        self.spline_extrapolation_rb = QtGui.QRadioButton("Spline")
        self.spline_extrapolation_cutoff_lbl = QtGui.QLabel('Cutoff:')
        self.spline_extrapolation_cutoff_txt = QtGui.QLineEdit('0.5')
        self.spline_extrapolation_q_max_lbl = QtGui.QLabel('Q Max:')
        self.spline_extrapolation_q_max_txt = QtGui.QLineEdit('1.5')

    def style_widgets(self):

        self.poly_extrapolation_q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.poly_extrapolation_q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.poly_extrapolation_q_max_txt.setMaximumWidth(50)

        self.spline_extrapolation_cutoff_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_extrapolation_cutoff_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.spline_extrapolation_q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.spline_extrapolation_q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.spline_extrapolation_cutoff_txt.setValidator(QtGui.QDoubleValidator())
        self.spline_extrapolation_q_max_txt.setValidator(QtGui.QDoubleValidator())

        self.spline_extrapolation_cutoff_txt.setMaximumWidth(50)
        self.spline_extrapolation_q_max_txt.setMaximumWidth(50)

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

        self.rb_ver_layout.addWidget(self.step_extrapolation_rb)

        self.rb_ver_layout.addWidget(self.linear_extrapolation_rb)

        self.rb_ver_layout.addWidget(self.poly_extrapolation_rb)
        self.poly_extrapolation_widget = QtGui.QWidget(self)
        self.poly_extrapolation_layout = QtGui.QGridLayout()
        self.poly_extrapolation_layout.setContentsMargins(0, 0, 0, 0)
        self.poly_extrapolation_layout.setSpacing(5)

        self.poly_extrapolation_layout.addItem(QtGui.QSpacerItem(10, 10), 0, 0)
        self.poly_extrapolation_layout.addWidget(self.poly_extrapolation_q_max_lbl, 0, 1)
        self.poly_extrapolation_layout.addWidget(self.poly_extrapolation_q_max_txt, 0, 2)
        self.poly_extrapolation_layout.addWidget(self.poly_extrapolation_replace_cb, 1, 2)
        self.poly_extrapolation_layout.addWidget(QtGui.QLabel('A-1'), 0, 3)

        self.poly_extrapolation_widget.setLayout(self.poly_extrapolation_layout)

        self.rb_ver_layout.addWidget(self.poly_extrapolation_widget)
        self.rb_ver_layout.addWidget(self.spline_extrapolation_rb)

        self.spline_extrapolation_widget = QtGui.QWidget(self)
        self.spline_extrapolation_parameter_layout = QtGui.QGridLayout()
        self.spline_extrapolation_parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.spline_extrapolation_parameter_layout.setSpacing(5)

        self.spline_extrapolation_parameter_layout.addItem(QtGui.QSpacerItem(10, 10), 0, 0)
        self.spline_extrapolation_parameter_layout.addWidget(self.spline_extrapolation_cutoff_lbl, 0, 1)
        self.spline_extrapolation_parameter_layout.addWidget(self.spline_extrapolation_cutoff_txt, 0, 2)

        self.spline_extrapolation_parameter_layout.addWidget(self.spline_extrapolation_q_max_lbl, 1, 1)
        self.spline_extrapolation_parameter_layout.addWidget(self.spline_extrapolation_q_max_txt, 1, 2)
        self.spline_extrapolation_parameter_layout.addWidget(QtGui.QLabel('A'), 1, 3)

        self.spline_extrapolation_widget.setLayout(self.spline_extrapolation_parameter_layout)

        self.rb_ver_layout.addWidget(self.spline_extrapolation_widget)
        self.rb_horizontal_layout.addLayout(self.rb_ver_layout)

        self.rb_widget.setLayout(self.rb_horizontal_layout)
        self.vertical_layout.addWidget(self.rb_widget)
        self.setLayout(self.vertical_layout)

    def disable_rb_widgets(self):
        self.rb_widget.setEnabled(False)

    def enable_rb_widgets(self):
        self.rb_widget.setEnabled(True)

    def disable_spline_widgets(self):
        self.spline_extrapolation_widget.setEnabled(False)

    def enable_spline_widgets(self):
        self.spline_extrapolation_widget.setEnabled(True)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.rb_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.extrapolation_parameters_changed.emit)

        self.linear_extrapolation_rb.toggled.connect(self.extrapolation_parameters_changed.emit)
        self.linear_extrapolation_rb.toggled.connect(self.update_visibility)

        self.spline_extrapolation_cutoff_txt.editingFinished.connect(self.txt_changed)
        self.spline_extrapolation_q_max_txt.editingFinished.connect(self.txt_changed)

    def update_visibility(self):
        if self.spline_extrapolation_rb.isChecked():
            self.enable_spline_widgets()
        else:
            self.disable_spline_widgets()

    def txt_changed(self):
        if self.spline_extrapolation_cutoff_txt.isModified() or \
                self.spline_extrapolation_q_max_txt.isModified():
            self.extrapolation_parameters_changed.emit()

            self.spline_extrapolation_cutoff_txt.setModified(False)
            self.spline_extrapolation_q_max_txt.setModified(False)

    def get_extrapolation_method(self):
        if not self.activate_cb.isChecked():
            return None
        elif self.linear_extrapolation_rb.isChecked():
            return "linear"
        elif self.poly_extrapolation_rb.isChecked():
            return "poly"
        elif self.spline_extrapolation_rb.isChecked():
            return "spline"
        elif self.step_extrapolation_rb.isChecked():
            return 'step'

    def get_extrapolation_parameters(self):
        if self.spline_extrapolation_rb.isChecked():
            return {'cutoff': float(str(self.spline_extrapolation_cutoff_txt.text())),
                    'q_max': float(str(self.spline_extrapolation_q_max_txt.text()))}
        elif self.poly_extrapolation_rb.isChecked():
            return {'q_max': float(str(self.poly_extrapolation_q_max_txt.text())),
                    'replace': True}
        else:
            return {}

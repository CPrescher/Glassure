# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal

from ..custom_widgets import HorizontalLine, HorizontalSpacerItem


class ExtrapolationWidget(QtGui.QWidget):
    extrapolation_parameters_changed = Signal()

    def __init__(self, *args):
        super(ExtrapolationWidget, self).__init__(*args)

        self.create_widgets()
        self.create_layout()
        self.style_widgets()
        self.create_signals()

        self.update_visibility()
        self.rb_widget.setVisible(False)
        self.activate_cb.setChecked(True)

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")

        self.step_extrapolation_rb = MyRadioButton('Step')
        self.linear_extrapolation_rb = MyRadioButton("Linear")
        self.poly_extrapolation_rb = MyRadioButton("Polynomial")
        self.spline_extrapolation_rb = MyRadioButton("Spline")
        self.step_extrapolation_rb.setChecked(True)

        self.q_max_lbl = QtGui.QLabel("Q Max:")
        self.q_max_txt = QtGui.QLineEdit("2")
        self.replace_cb = QtGui.QCheckBox("replace")

        self.rb_button_group = QtGui.QButtonGroup()
        self.rb_button_group.addButton(self.step_extrapolation_rb)
        self.rb_button_group.addButton(self.linear_extrapolation_rb)
        self.rb_button_group.addButton(self.poly_extrapolation_rb)
        self.rb_button_group.addButton(self.spline_extrapolation_rb)

    def style_widgets(self):
        self.q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setMaximumWidth(50)
        self.q_max_txt.setValidator(QtGui.QDoubleValidator())

    def create_layout(self):
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.vertical_layout.setSpacing(5)

        self.vertical_layout.addWidget(self.activate_cb)
        self.vertical_layout.addWidget(HorizontalLine())

        self.rb_layout = QtGui.QGridLayout()
        self.rb_layout.setContentsMargins(5, 5, 5, 5)
        self.rb_layout.setSpacing(8)

        self.rb_layout.addWidget(self.step_extrapolation_rb, 0, 0)
        self.rb_layout.addWidget(self.linear_extrapolation_rb, 0, 1)
        self.rb_layout.addWidget(self.poly_extrapolation_rb, 1, 0)
        self.rb_layout.addWidget(self.spline_extrapolation_rb, 1, 1)

        self.rb_widget = QtGui.QWidget(self)
        self.rb_widget.setLayout(self.rb_layout)
        self.vertical_layout.addWidget(self.rb_widget)

        self.parameter_layout = QtGui.QGridLayout()
        self.parameter_layout.addWidget(HorizontalLine(), 0, 0, 1, 5)
        self.parameter_layout.setContentsMargins(0, 0, 0, 0)
        self.parameter_layout.setSpacing(5)
        self.parameter_layout.addItem(HorizontalSpacerItem(), 0, 0)

        self.parameter_layout.addWidget(self.q_max_lbl, 1, 0)
        self.parameter_layout.addWidget(self.q_max_txt)

        self.parameter_layout.addWidget(QtGui.QLabel('A'))
        self.parameter_layout.addWidget(self.replace_cb)

        self.parameter_widget = QtGui.QWidget(self)
        self.parameter_widget.setLayout(self.parameter_layout)
        self.vertical_layout.addWidget(self.parameter_widget)

        self.setLayout(self.vertical_layout)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.rb_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.extrapolation_parameters_changed.emit)

        self.rb_button_group.buttonReleased.connect(self.extrapolation_parameters_changed)
        self.rb_button_group.buttonReleased.connect(self.update_visibility)

        self.q_max_txt.editingFinished.connect(self.q_max_changed)
        self.replace_cb.stateChanged.connect(self.extrapolation_parameters_changed)

    def q_max_changed(self):
        if self.q_max_txt.isModified():
            self.extrapolation_parameters_changed.emit()
            self.q_max_txt.setModified(False)

    def update_visibility(self):
        self.parameter_widget.setVisible(self.spline_extrapolation_rb.isChecked() |
                                         self.poly_extrapolation_rb.isChecked())

    def txt_changed(self):
        if self.spline_extrapolation_cutoff_txt.isModified() or \
                self.spline_extrapolation_q_max_txt.isModified():
            self.extrapolation_parameters_changed.emit()

            self.spline_extrapolation_cutoff_txt.setModified(False)
            self.spline_extrapolation_q_max_txt.setModified(False)

    def get_extrapolation_method(self):
        if not self.activate_cb.isChecked():
            return None
        elif self.step_extrapolation_rb.isChecked():
            return 'step'
        elif self.linear_extrapolation_rb.isChecked():
            return "linear"
        elif self.poly_extrapolation_rb.isChecked():
            return "poly"
        elif self.spline_extrapolation_rb.isChecked():
            return "spline"

    def get_extrapolation_parameters(self):
        if self.spline_extrapolation_rb.isChecked() or self.poly_extrapolation_rb.isChecked():
            return {'q_max': float(str(self.q_max_txt.text())),
                    'replace': self.replace_cb.isChecked()}
        else:
            return {}


class MyRadioButton(QtGui.QPushButton):
    def __init__(self, *args):
        super(MyRadioButton, self).__init__(*args)
        self.setCheckable(True)
        self.setFlat(True)
        self.setMinimumHeight(25)

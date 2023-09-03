# -*- coding: utf-8 -*-

from qtpy import QtCore, QtGui, QtWidgets

from ..custom import HorizontalLine, HorizontalSpacerItem, FloatLineEdit, LabelAlignRight
from ...model.configuration import ExtrapolationConfiguration


class ExtrapolationWidget(QtWidgets.QWidget):
    extrapolation_parameters_changed = QtCore.Signal(ExtrapolationConfiguration)

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
        self.activate_cb = QtWidgets.QCheckBox("activate")

        self.step_extrapolation_rb = MyRadioButton('Step')
        self.linear_extrapolation_rb = MyRadioButton("Linear")
        self.poly_extrapolation_rb = MyRadioButton("Polynomial")
        self.spline_extrapolation_rb = MyRadioButton("Spline")
        self.step_extrapolation_rb.setChecked(True)

        self.s0_label = LabelAlignRight("S(Q=0):")
        self.s0_txt = FloatLineEdit("0")
        self.s0_auto_cb = QtWidgets.QCheckBox("auto")
        self.s0_auto_cb.setToolTip("Automatically determines S(Q=0) from the form factors.")
        self.s0_auto_cb.setChecked(True)

        self.options_gb = QtWidgets.QGroupBox(self)
        self.q_max_lbl = LabelAlignRight("Fit Q_max:")
        self.q_max_txt = FloatLineEdit("2")
        self.q_max_unit_lbl = LabelAlignRight("A")
        self.replace_cb = QtWidgets.QCheckBox("replace")
        self.replace_cb.setToolTip("Replace data with extrapolated data in overlapping region.")

        self.rb_button_group = QtWidgets.QButtonGroup()
        self.rb_button_group.addButton(self.step_extrapolation_rb)
        self.rb_button_group.addButton(self.linear_extrapolation_rb)
        self.rb_button_group.addButton(self.poly_extrapolation_rb)
        self.rb_button_group.addButton(self.spline_extrapolation_rb)

    def style_widgets(self):
        self.q_max_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.q_max_txt.setMaximumWidth(50)
        self.s0_txt.setMaximumWidth(50)

    def create_layout(self):
        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.vertical_layout.setSpacing(5)

        self.vertical_layout.addWidget(self.activate_cb)
        self.vertical_layout.addWidget(HorizontalLine())

        self.rb_layout = QtWidgets.QGridLayout()
        self.rb_layout.setContentsMargins(5, 5, 5, 5)
        self.rb_layout.setSpacing(8)

        self.rb_layout.addWidget(self.step_extrapolation_rb, 0, 0)
        self.rb_layout.addWidget(self.linear_extrapolation_rb, 0, 1)
        self.rb_layout.addWidget(self.poly_extrapolation_rb, 1, 0)
        self.rb_layout.addWidget(self.spline_extrapolation_rb, 1, 1)

        self.rb_widget = QtWidgets.QWidget(self)
        self.rb_widget.setLayout(self.rb_layout)
        self.vertical_layout.addWidget(self.rb_widget)

        self.options_layout = QtWidgets.QGridLayout()
        self.options_layout.setSpacing(5)
        self.options_layout.setColumnStretch(0, 1)

        self.options_layout.addWidget(self.s0_label, 0, 1)
        self.options_layout.addWidget(self.s0_txt, 0, 2)
        self.options_layout.addWidget(self.s0_auto_cb, 0, 4)

        self.options_layout.addWidget(self.q_max_lbl, 1, 1)
        self.options_layout.addWidget(self.q_max_txt, 1, 2)
        self.options_layout.addWidget(self.q_max_unit_lbl, 1, 3)
        self.options_layout.addWidget(self.replace_cb, 1, 4)

        self.options_gb.setLayout(self.options_layout)

        self.vertical_layout.addWidget(self.options_gb)
        self.setLayout(self.vertical_layout)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.rb_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.options_gb.setVisible)
        self.activate_cb.stateChanged.connect(self.emit_changed_signal)

        self.rb_button_group.buttonReleased.connect(self.emit_changed_signal)
        self.rb_button_group.buttonReleased.connect(self.update_visibility)

        self.q_max_txt.editingFinished.connect(self.emit_changed_signal)
        self.replace_cb.stateChanged.connect(self.emit_changed_signal)

        self.s0_txt.editingFinished.connect(self.emit_changed_signal)
        self.s0_auto_cb.stateChanged.connect(self.emit_changed_signal)

    def emit_changed_signal(self):
        self.extrapolation_parameters_changed.emit(self.get_configuration())

    def update_visibility(self):
        visible_flag = not (self.step_extrapolation_rb.isChecked() | self.linear_extrapolation_rb.isChecked())
        self.q_max_lbl.setVisible(visible_flag)
        self.q_max_unit_lbl.setVisible(visible_flag)
        self.q_max_txt.setVisible(visible_flag)
        self.replace_cb.setVisible(visible_flag)

    def get_configuration(self) -> ExtrapolationConfiguration:
        config = ExtrapolationConfiguration()
        config.activate = self.activate_cb.isChecked()
        config.method = self.get_method()
        config.fit_q_max = float(str(self.q_max_txt.text()))
        config.fit_replace = self.replace_cb.isChecked()
        config.s0 = float(str(self.s0_txt.text()))
        config.s0_auto = self.s0_auto_cb.isChecked()
        return config

    def update_configuration(self, config: ExtrapolationConfiguration):
        self.activate_cb.setChecked(config.activate)
        self.set_extrapolation_method(config.method)
        self.q_max_txt.setText(f"{config.fit_q_max:.2f}")
        self.replace_cb.setChecked(config.fit_replace)
        self.s0_txt.setText(f"{config.s0:.2f}")
        self.s0_auto_cb.setChecked(config.s0_auto)
        self.update_visibility()

    def get_method(self):
        if self.step_extrapolation_rb.isChecked():
            return 'step'
        elif self.linear_extrapolation_rb.isChecked():
            return "linear"
        elif self.poly_extrapolation_rb.isChecked():
            return "poly"
        elif self.spline_extrapolation_rb.isChecked():
            return "spline"

    def set_extrapolation_method(self, method):
        if method == 'step':
            self.step_extrapolation_rb.setChecked(True)
        elif method == "linear":
            self.linear_extrapolation_rb.setChecked(True)
        elif method == "poly":
            self.poly_extrapolation_rb.setChecked(True)
        elif method == "spline":
            self.spline_extrapolation_rb.setChecked(True)

        self.update_visibility()


class MyRadioButton(QtWidgets.QPushButton):
    def __init__(self, *args):
        super(MyRadioButton, self).__init__(*args)
        self.setCheckable(True)
        self.setFlat(True)
        self.setMinimumHeight(25)

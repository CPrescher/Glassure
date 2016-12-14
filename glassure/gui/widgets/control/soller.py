# -*- coding: utf8 -*-

from ...qt import QtGui, QtWidgets, Signal

from ..custom import HorizontalLine, ValueLabelTxtPair


class SollerWidget(QtWidgets.QWidget):
    soller_parameters_changed = Signal()

    def __init__(self, *args):
        super(SollerWidget, self).__init__(*args)

        self.create_layout_and_widgets()
        self.style_widgets()
        self.create_signals()

        self.param_widget.setVisible(False)
        self.activate_cb.setChecked(False)

    def create_layout_and_widgets(self):
        self.main_layout = QtWidgets.QVBoxLayout()

        self.activate_cb = QtWidgets.QCheckBox("activate")
        self.main_layout.addWidget(self.activate_cb)
        self.main_layout.addWidget(HorizontalLine())

        self.param_layout = QtWidgets.QGridLayout()
        self.thickness_txt = ValueLabelTxtPair("Sample thickness:", 0.2, "mm", self.param_layout, 0)
        self.wavelength_txt = ValueLabelTxtPair("X-ray wavelength:", 0.31, "A", self.param_layout, 1)
        self.param_layout.addWidget(HorizontalLine(), 2, 0, 1, 3)
        self.inner_radius_txt = ValueLabelTxtPair("Inner radius:", '', "mm", self.param_layout, 4)
        self.outer_radius_txt = ValueLabelTxtPair("Outer radius:", '', "mm", self.param_layout, 5)
        self.inner_width_txt = ValueLabelTxtPair("Inner width:", '', "mm", self.param_layout, 6)
        self.outer_width_txt = ValueLabelTxtPair("Outer width:", '', "mm", self.param_layout, 7)
        self.inner_length_txt = ValueLabelTxtPair("Inner length:", '', "mm", self.param_layout, 8)
        self.outer_length_txt = ValueLabelTxtPair("Inner length:", '', "mm", self.param_layout, 9)

        self.param_widget = QtWidgets.QWidget()
        self.param_widget.setLayout(self.param_layout)

        self.main_layout.addWidget(self.param_widget)
        self.setLayout(self.main_layout)

    def style_widgets(self):
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.param_layout.setContentsMargins(50, 0, 0, 0)
        self.param_layout.setVerticalSpacing(7)

    #

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.param_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.soller_parameters_changed.emit)

        self.thickness_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.wavelength_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.inner_radius_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.outer_radius_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.inner_width_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.outer_width_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.inner_length_txt.editingFinished.connect(self.soller_parameters_changed.emit)
        self.outer_length_txt.editingFinished.connect(self.soller_parameters_changed.emit)

    def get_parameters(self):
        return {"sample_thickness": self.thickness_txt.get_value(),
                "wavelength": self.wavelength_txt.get_value(),
                "inner_radius": self.inner_radius_txt.get_value(),
                "outer_radius": self.outer_radius_txt.get_value(),
                "inner_width": self.inner_width_txt.get_value(),
                "outer_width": self.outer_width_txt.get_value(),
                "inner_length": self.inner_length_txt.get_value(),
                "outer_length": self.outer_length_txt.get_value()}

    def set_parameters(self, parameter):
        self.blockSignals(True)
        self.thickness_txt.set_value(parameter["sample_thickness"])
        self.wavelength_txt.set_value(parameter["wavelength"])
        self.inner_radius_txt.set_value(parameter["inner_radius"])
        self.outer_radius_txt.set_value(parameter["outer_radius"])
        self.inner_width_txt.set_value(parameter["inner_width"])
        self.outer_width_txt.set_value(parameter["outer_width"])
        self.inner_length_txt.set_value(parameter["inner_length"])
        self.outer_length_txt.set_value(parameter["outer_length"])
        self.blockSignals(False)

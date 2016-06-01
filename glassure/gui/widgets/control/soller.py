# -*- coding: utf8 -*-

from ...qt import QtCore, QtGui, Signal

from ..custom import NumberTextField, LabelAlignRight, HorizontalLine


class SollerWidget(QtGui.QWidget):
    soller_parameters_changed = Signal()

    def __init__(self, *args):
        super(SollerWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

        self.param_widget.setVisible(False)
        self.activate_cb.setChecked(False)

    def create_widgets(self):
        self.activate_cb = QtGui.QCheckBox("activate")


    def style_widgets(self):
        pass

    def create_layout(self):
        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.main_layout.addWidget(self.activate_cb)
        self.main_layout.addWidget(HorizontalLine())

        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)

        self.param_widget = QtGui.QWidget()
        self.param_widget.setLayout(self.grid_layout)

        self.main_layout.addWidget(self.param_widget)

        self.setLayout(self.main_layout)

    def create_signals(self):
        self.activate_cb.stateChanged.connect(self.param_widget.setVisible)
        self.activate_cb.stateChanged.connect(self.soller_parameters_changed.emit)

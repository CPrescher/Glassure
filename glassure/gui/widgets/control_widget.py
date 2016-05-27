# -*- coding: utf8 -*-

from ..qt import QtGui

from .control_widgets import CompositionWidget, DataWidget, OptimizationWidget, \
    OptionsWidget, DensityOptimizationWidget, ExtrapolationWidget, DiamondWidget, ConfigurationWidget
from .custom_widgets import ExpandableBox


class LeftControlWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(LeftControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setSpacing(8)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.data_widget = DataWidget()
        self.composition_widget = CompositionWidget()
        self.options_widget = OptionsWidget()
        self.density_optimization_widget = DensityOptimizationWidget()
        self.extrapolation_widget = ExtrapolationWidget()

        self.vertical_layout.addWidget(ExpandableBox(self.data_widget, "Data"))
        self.vertical_layout.addWidget(ExpandableBox(self.composition_widget, "Composition"))
        self.vertical_layout.addWidget(ExpandableBox(self.options_widget, "Options"))
        self.vertical_layout.addWidget(ExpandableBox(self.extrapolation_widget, "Extrapolation"))

        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(20, 50, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.Expanding))

        self.setLayout(self.vertical_layout)


class RightControlWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(RightControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setSpacing(8)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.configuration_widget = ConfigurationWidget()
        self.optimization_widget = OptimizationWidget()
        self.density_optimization_widget = DensityOptimizationWidget()
        self.diamond_widget = DiamondWidget()

        self.vertical_layout.addWidget(ExpandableBox(self.configuration_widget, "Configurations"))
        self.vertical_layout.addWidget(ExpandableBox(self.optimization_widget, "Optimization"))
        self.vertical_layout.addWidget(ExpandableBox(self.density_optimization_widget, "Density Optimization", True))
        self.vertical_layout.addWidget(ExpandableBox(self.diamond_widget, "Diamond Correction", True))

        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(20, 50, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.MinimumExpanding))

        self.setLayout(self.vertical_layout)

# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtGui

from ControlWidgets import CompositionWidget, DataWidget, OptimizationWidget, \
    OptionsWidget, DensityOptimizationWidget, InterpolationWidget
from CustomWidgets import ExpandableBox


class LeftControlWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(LeftControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setSpacing(8)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.data_widget = DataWidget()
        self.composition_widget = CompositionWidget()
        self.options_widget = OptionsWidget()
        self.optimization_widget = OptimizationWidget()
        self.density_optimization_widget = DensityOptimizationWidget()
        self.interpolation_widget = InterpolationWidget()

        self.vertical_layout.addWidget(ExpandableBox(self.data_widget, "Data"))
        self.vertical_layout.addWidget(ExpandableBox(self.composition_widget, "Composition"))
        self.vertical_layout.addWidget(ExpandableBox(self.options_widget, "Options"))
        self.vertical_layout.addWidget(ExpandableBox(self.interpolation_widget, "Interpolation"))

        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(20, 50, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.Expanding))

        self.setLayout(self.vertical_layout)

class RightControlWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(RightControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setSpacing(8)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.data_widget = DataWidget()
        self.composition_widget = CompositionWidget()
        self.options_widget = OptionsWidget()
        self.optimization_widget = OptimizationWidget()
        self.density_optimization_widget = DensityOptimizationWidget()

        self.vertical_layout.addWidget(ExpandableBox(self.optimization_widget, "Optimization"))
        self.vertical_layout.addWidget(ExpandableBox(self.density_optimization_widget, "Density Optimization"))

        self.vertical_layout.addSpacerItem(QtGui.QSpacerItem(20, 50, QtGui.QSizePolicy.Fixed,
                                                             QtGui.QSizePolicy.Expanding))

        self.setLayout(self.vertical_layout)

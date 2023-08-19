# -*- coding: utf-8 -*-

import sys
import os

from ... import __version__

from qtpy import QtWidgets, QtCore

from .control import CompositionWidget, DataWidget, OptimizationWidget, OptionsWidget, DensityOptimizationWidget, \
    ExtrapolationWidget, DiamondWidget, ConfigurationWidget, SollerWidget, TransferFunctionWidget
from .custom import PatternWidget

from .custom import ExpandableBox


class GlassureWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(GlassureWidget, self).__init__(*args, **kwargs)
        self.horizontal_layout = QtWidgets.QHBoxLayout(self)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)

        self.pattern_widget = PatternWidget()
        self.left_control_widget = LeftControlWidget()
        self.right_control_widget = RightControlWidget()

        self.left_control_scroll_area = QtWidgets.QScrollArea()
        self.left_control_scroll_area.setWidget(self.left_control_widget)
        self.left_control_scroll_area.setWidgetResizable(True)

        self.left_control_scroll_area.setMaximumWidth(300)
        self.left_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.right_control_scroll_area = QtWidgets.QScrollArea()
        self.right_control_scroll_area.setWidget(self.right_control_widget)
        self.right_control_scroll_area.setWidgetResizable(True)

        self.right_control_scroll_area.setMaximumWidth(300)
        self.right_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.horizontal_layout.addWidget(self.left_control_scroll_area)
        self.horizontal_layout.addWidget(self.pattern_widget)
        self.horizontal_layout.addWidget(self.right_control_scroll_area)

        self.horizontal_layout.setStretch(0, 0)
        self.horizontal_layout.setStretch(1, 100)
        self.horizontal_layout.setStretch(2, 0)

        self.setLayout(self.horizontal_layout)

        self.load_stylesheet()

        self.create_widget_shortcuts()
        self.create_function_shortcuts()

        self.setWindowTitle("Glassure v{}".format(__version__))

    def create_widget_shortcuts(self):
        self.load_data_btn = self.left_control_widget.data_widget.file_widget.load_data_btn
        self.load_bkg_btn = self.left_control_widget.data_widget.file_widget.load_background_btn
        self.reset_bkg_btn = self.left_control_widget.data_widget.file_widget.reset_background_btn
        self.data_filename_lbl = self.left_control_widget.data_widget.file_widget.data_filename_lbl
        self.bkg_filename_lbl = self.left_control_widget.data_widget.file_widget.background_filename_lbl

        self.bkg_scaling_sb = self.left_control_widget.data_widget.background_options_gb.scale_sb
        self.bkg_scaling_step_txt = self.left_control_widget.data_widget.background_options_gb.scale_step_txt

        self.smooth_sb = self.left_control_widget.data_widget.smooth_gb.smooth_sb
        self.smooth_step_txt = self.left_control_widget.data_widget.smooth_gb.smooth_step_txt

        self.add_element_btn = self.left_control_widget.composition_widget.add_element_btn
        self.delete_element_btn = self.left_control_widget.composition_widget.delete_element_btn
        self.composition_tw = self.left_control_widget.composition_widget.composition_tw
        self.density_txt = self.left_control_widget.composition_widget.density_txt

        self.q_max_txt = self.left_control_widget.options_widget.q_max_txt
        self.q_min_txt = self.left_control_widget.options_widget.q_min_txt
        self.r_max_txt = self.left_control_widget.options_widget.r_max_txt
        self.r_min_txt = self.left_control_widget.options_widget.r_min_txt
        self.use_modification_cb = self.left_control_widget.options_widget.modification_fcn_cb

        self.activate_extrapolation_cb = self.left_control_widget.extrapolation_widget.activate_cb
        self.extrapolation_q_max_txt = self.left_control_widget.extrapolation_widget.q_max_txt

        self.optimize_activate_cb = self.right_control_widget.optimization_widget.activate_cb
        self.optimize_r_cutoff_txt = self.right_control_widget.optimization_widget.r_cutoff_txt
        self.optimize_iterations_txt = self.right_control_widget.optimization_widget.optimize_iterations_txt
        self.optimize_attenuation_sb = self.right_control_widget.optimization_widget.attenuation_factor_sb

        self.save_sq_btn = self.pattern_widget.mouse_position_widget.save_sq_btn
        self.save_gr_btn = self.pattern_widget.mouse_position_widget.save_gr_btn

        self.configuration_widget = self.right_control_widget.configuration_widget
        self.freeze_configuration_btn = self.right_control_widget.configuration_widget.freeze_btn
        self.remove_configuration_btn = self.right_control_widget.configuration_widget.remove_btn
        self.configuration_tw = self.right_control_widget.configuration_widget.configuration_tw

        self.soller_widget = self.right_control_widget.soller_widget
        self.soller_active_cb = self.right_control_widget.soller_widget.activate_cb

        self.transfer_widget = self.right_control_widget.transfer_widget
        self.transfer_active_cb = self.right_control_widget.transfer_widget.activate_cb

    def create_function_shortcuts(self):
        self.set_composition = self.left_control_widget.composition_widget.set_composition
        self.get_composition = self.left_control_widget.composition_widget.get_composition
        self.get_sf_source = self.left_control_widget.composition_widget.get_sf_source
        self.set_sf_source = self.left_control_widget.composition_widget.set_sf_source

        self.get_density = self.left_control_widget.composition_widget.get_density

        self.get_parameter = self.left_control_widget.options_widget.get_parameter

        self.set_extrapolation_method = self.left_control_widget.extrapolation_widget.set_extrapolation_method
        self.get_extrapolation_method = self.left_control_widget.extrapolation_widget.get_extrapolation_method
        self.set_extrapolation_parameters = self.left_control_widget.extrapolation_widget.set_extrapolation_parameters
        self.get_extrapolation_parameters = self.left_control_widget.extrapolation_widget.get_extrapolation_parameters

        self.set_optimization_parameter = self.right_control_widget.optimization_widget.set_parameter
        self.get_optimization_parameter = self.right_control_widget.optimization_widget.get_parameter

        self.set_soller_parameter = self.right_control_widget.soller_widget.set_parameters
        self.get_soller_parameter = self.right_control_widget.soller_widget.get_parameters

    def show(self):
        QtWidgets.QWidget.show(self)
        if sys.platform == "darwin":
            self.setWindowState(
                self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            self.activateWindow()
            self.raise_()

    def load_stylesheet(self):
        stylesheet_file = open(os.path.join(module_path(), "DioptasStyle.qss"), 'r')
        stylesheet_str = stylesheet_file.read()
        self.setStyleSheet(stylesheet_str)


class LeftControlWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(LeftControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtWidgets.QVBoxLayout()
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

        self.vertical_layout.addSpacerItem(QtWidgets.QSpacerItem(20, 50, QtWidgets.QSizePolicy.Fixed,
                                                                 QtWidgets.QSizePolicy.Expanding))

        self.setLayout(self.vertical_layout)


class RightControlWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(RightControlWidget, self).__init__(*args, **kwargs)
        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setSpacing(8)
        self.vertical_layout.setContentsMargins(5, 5, 5, 5)

        self.configuration_widget = ConfigurationWidget()
        self.optimization_widget = OptimizationWidget()
        self.density_optimization_widget = DensityOptimizationWidget()
        self.diamond_widget = DiamondWidget()
        self.soller_widget = SollerWidget()
        self.transfer_widget = TransferFunctionWidget()

        self.vertical_layout.addWidget(ExpandableBox(self.configuration_widget, "Configurations"))
        self.vertical_layout.addWidget(ExpandableBox(self.optimization_widget, "Optimization"))
        self.vertical_layout.addWidget(ExpandableBox(self.density_optimization_widget, "Density Optimization", True))
        self.vertical_layout.addWidget(ExpandableBox(self.diamond_widget, "Diamond Correction", True))
        self.vertical_layout.addWidget(ExpandableBox(self.soller_widget, "Soller Slit Correction", True))
        self.vertical_layout.addWidget(ExpandableBox(self.transfer_widget, "Transfer Function Correction", True))

        self.vertical_layout.addSpacerItem(QtWidgets.QSpacerItem(20, 50, QtWidgets.QSizePolicy.Fixed,
                                                                 QtWidgets.QSizePolicy.MinimumExpanding))

        self.setLayout(self.vertical_layout)


def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def module_path():
    return os.path.dirname(__file__)

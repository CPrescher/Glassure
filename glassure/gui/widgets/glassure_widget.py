# -*- coding: utf8 -*-

import sys
import os

from core import __version__

from ..qt import QtGui, QtCore

from gui.widgets.custom_widgets import SpectrumWidget
from .control_widget import LeftControlWidget, RightControlWidget


class GlassureWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(GlassureWidget, self).__init__(*args, **kwargs)
        self.horizontal_layout = QtGui.QHBoxLayout(self)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)

        self.spectrum_widget = SpectrumWidget()
        self.left_control_widget = LeftControlWidget()
        self.right_control_widget = RightControlWidget()

        self.left_control_scroll_area = QtGui.QScrollArea()
        self.left_control_scroll_area.setWidget(self.left_control_widget)
        self.left_control_scroll_area.setWidgetResizable(True)

        self.left_control_scroll_area.setMaximumWidth(300)
        self.left_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.right_control_scroll_area = QtGui.QScrollArea()
        self.right_control_scroll_area.setWidget(self.right_control_widget)
        self.right_control_scroll_area.setWidgetResizable(True)

        self.right_control_scroll_area.setMaximumWidth(300)
        self.right_control_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.horizontal_layout.addWidget(self.left_control_scroll_area)
        self.horizontal_layout.addWidget(self.spectrum_widget)
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

        self.bkg_scaling_sb = self.left_control_widget.data_widget.background_options_gb.scale_sb
        self.bkg_scaling_step_txt = self.left_control_widget.data_widget.background_options_gb.scale_step_txt

        self.smooth_sb = self.left_control_widget.data_widget.smooth_gb.smooth_sb
        self.smooth_step_txt = self.left_control_widget.data_widget.smooth_gb.smooth_step_txt

        self.add_element_btn = self.left_control_widget.composition_widget.add_element_btn
        self.delete_element_btn = self.left_control_widget.composition_widget.delete_element_btn

        self.q_max_txt = self.left_control_widget.options_widget.q_max_txt
        self.q_min_txt = self.left_control_widget.options_widget.q_min_txt
        self.r_max_txt = self.left_control_widget.options_widget.r_max_txt
        self.r_min_txt = self.left_control_widget.options_widget.r_min_txt
        self.use_modification_cb = self.left_control_widget.options_widget.modification_fcn_cb

        self.activate_interpolation_cb = self.left_control_widget.interpolation_widget.activate_cb

        self.save_sq_btn = self.spectrum_widget.mouse_position_widget.save_sq_btn
        self.save_gr_btn = self.spectrum_widget.mouse_position_widget.save_gr_btn

    def create_function_shortcuts(self):
        self.get_composition = self.left_control_widget.composition_widget.get_composition
        self.get_density = self.left_control_widget.composition_widget.get_density

        self.get_parameter = self.left_control_widget.options_widget.get_parameter
        self.get_interpolation_method = self.left_control_widget.interpolation_widget.get_interpolation_method
        self.get_interpolation_parameters = self.left_control_widget.interpolation_widget.get_interpolation_parameters
        self.get_optimization_parameter = self.right_control_widget.optimization_widget.get_parameter

    def show(self):
        QtGui.QWidget.show(self)
        if sys.platform == "darwin":
            self.main_widget.setWindowState(
                self.main_widget.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
            self.main_widget.activateWindow()
            self.main_widget.raise_()

    def load_stylesheet(self):
        stylesheet_file = open(os.path.join(module_path(), "DioptasStyle.qss"), 'r')
        stylesheet_str = stylesheet_file.read()
        self.setStyleSheet(stylesheet_str)


def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def module_path():
    return os.path.dirname(__file__)

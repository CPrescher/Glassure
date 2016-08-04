# -*- coding: utf8 -*-

import os

import numpy as np

from ..qt import QtGui, QtCore
import pyqtgraph as pg

# # Switch to using white background and black foreground
pg.setConfigOption('useOpenGL', False)
pg.setConfigOption('leftButtonPan', False)
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')
pg.setConfigOption('antialias', True)

from ..widgets.glassure import GlassureWidget
from ..model.glassure import GlassureModel

from .configuration import ConfigurationController
from .soller import SollerController
from .transfer import TransferFunctionController


class GlassureController(object):
    def __init__(self):
        self.main_widget = GlassureWidget()

        self.model = GlassureModel()
        self.working_directory = ''
        self.sq_directory = ''
        self.gr_directory = ''
        self.connect_signals()

        self.configuration_controller = ConfigurationController(self.main_widget, self.model)
        self.soller_controller = SollerController(self.main_widget, self.model)
        self.transfer_controller = TransferFunctionController(self.main_widget, self.model)

    def show_window(self):
        """
        Displays the main window on the screen and makes it active
        """
        self.main_widget.show()

    def connect_signals(self):
        """
        Connects Gui signals with the model and model signals with the GUI.
        """

        # model

        self.model.data_changed.connect(self.model_changed)

        self.connect_click_function(self.main_widget.load_data_btn, self.load_data)
        self.connect_click_function(self.main_widget.load_bkg_btn, self.load_bkg)

        # connecting background scaling and smoothing of the original data
        self.main_widget.bkg_scaling_sb.valueChanged.connect(self.bkg_scale_changed)
        self.main_widget.smooth_sb.valueChanged.connect(self.smooth_changed)

        # updating the composition
        self.connect_click_function(self.main_widget.add_element_btn, self.add_element_btn_clicked)
        self.connect_click_function(self.main_widget.delete_element_btn, self.delete_element_btn_clicked)
        self.main_widget.left_control_widget.composition_widget.composition_changed.connect(self.update_model)

        # updating the calculation parameters
        self.main_widget.left_control_widget.options_widget.options_parameters_changed.connect(self.update_model)
        self.main_widget.left_control_widget.extrapolation_widget.extrapolation_parameters_changed.connect(
            self.update_model)

        # optimization controls

        self.main_widget.right_control_widget.optimization_widget.plot_progress_cb.stateChanged.connect(
            self.update_plot_progress
        )
        self.main_widget.right_control_widget.optimization_widget.optimization_parameters_changed.connect(
            self.update_model
        )

        self.main_widget.right_control_widget.density_optimization_widget.optimize_btn.clicked.connect(
            self.optimize_density)

        # Diamond controls
        self.main_widget.right_control_widget.diamond_widget.diamond_txt.editingFinished.connect(
            self.diamond_content_changed)
        self.main_widget.right_control_widget.diamond_widget.diamond_optimize_btn.clicked.connect(
            self.optimize_diamond_btn_clicked
        )

        # Saving the resulting data
        self.connect_click_function(self.main_widget.save_sq_btn, self.save_sq_btn_clicked)
        self.connect_click_function(self.main_widget.save_gr_btn, self.save_gr_btn_clicked)

    def connect_click_function(self, emitter, function):
        self.main_widget.connect(emitter, QtCore.SIGNAL('clicked()'), function)

    def load_data(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(
                self.main_widget, caption="Load Spectrum", directory=self.working_directory))

        if filename is not '':
            self.model.load_data(filename)
            self.working_directory = os.path.dirname(filename)
            self.main_widget.left_control_widget.data_widget.file_widget.data_filename_lbl.setText(
                os.path.basename(filename))

    def load_bkg(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(self.main_widget, "Load background data",
                                                             directory=self.working_directory))

        if filename is not None and filename != '':
            self.model.load_bkg(filename)
            self.working_directory = os.path.dirname(filename)
            self.main_widget.left_control_widget.data_widget.file_widget.background_filename_lbl.setText(
                os.path.basename(filename))

    def model_changed(self):
        if self.model.original_pattern is not None:
            self.main_widget.spectrum_widget.plot_spectrum(self.model.original_pattern)
        if self.model.background_pattern is not None:
            self.main_widget.spectrum_widget.plot_bkg(self.model.get_background_pattern())
        if self.model.sq_pattern is not None:
            self.main_widget.spectrum_widget.set_sq_pattern(self.model.sq_pattern, self.model.configuration_ind)
        if self.model.gr_pattern is not None:
            self.main_widget.spectrum_widget.set_gr_pattern(self.model.gr_pattern, self.model.configuration_ind)

        self.main_widget.left_control_widget.composition_widget.density_atomic_units_lbl. \
            setText("{:.4f}".format(self.model.atomic_density))

    def bkg_scale_changed(self, value):
        self.model.background_scaling = value

    def update_bkg_scale_step(self):
        value = np.float(self.main_widget.bkg_scale_step_txt.text())
        self.main_widget.bkg_scale_sb.setSingleStep(value)

    def update_bkg_offset_step(self):
        value = np.float(self.main_widget.bkg_offset_step_txt.text())
        self.main_widget.bkg_offset_sb.setSingleStep(value)

    def smooth_changed(self, value):
        self.model.set_smooth(value)

    def update_smooth_step(self):
        value = np.float(self.main_widget.smooth_step_txt.text())
        self.main_widget.smooth_sb.setSingleStep(value)

    def add_element_btn_clicked(self):
        self.main_widget.left_control_widget.composition_widget.add_element(element="Si", value=1.0)

    def delete_element_btn_clicked(self):
        cur_ind = self.main_widget.left_control_widget.composition_widget.composition_tw.currentRow()
        self.main_widget.left_control_widget.composition_widget.delete_element(cur_ind)

    def update_model(self):
        composition = self.main_widget.get_composition()
        density = self.main_widget.left_control_widget.composition_widget.get_density()

        q_min, q_max, r_min, r_max = self.main_widget.get_parameter()

        use_modification_fcn = self.main_widget.use_modification_cb.isChecked()
        extrapolation_method = self.main_widget.get_extrapolation_method()
        extrapolation_parameters = self.main_widget.get_extrapolation_parameters()

        optimize_active, r_cutoff, optimize_iterations, optimize_attenuation = self.main_widget.get_optimization_parameter()

        self.model.update_parameter(composition, density,
                                    q_min, q_max,
                                    r_min, r_max,
                                    use_modification_fcn,
                                    extrapolation_method,
                                    extrapolation_parameters,
                                    optimize_active,
                                    r_cutoff,
                                    optimize_iterations,
                                    optimize_attenuation
        )

    def update_plot_progress(self, bool):
        if bool:
            self.model.optimization_callback = self.plot_optimization_progress
        else:
            self.model.optimization_callback = None

    def plot_optimization_progress(self, sq_spectrum, fr_spectrum, gr_spectrum):
        self.main_widget.spectrum_widget.set_sq_pattern(sq_spectrum, self.model.configuration_ind)
        self.main_widget.spectrum_widget.set_gr_pattern(gr_spectrum, self.model.configuration_ind)
        QtGui.QApplication.processEvents()

    def optimize_density(self):
        density_min, density_max, bkg_min, bkg_max, iterations = \
            self.main_widget.left_control_widget.density_optimization_widget.get_parameters()
        self.model.optimize_density_and_scaling(
            density_min, density_max, bkg_min, bkg_max, iterations, output_txt=
            self.main_widget.right_control_widget.density_optimization_widget.optimization_output_txt,
            callback_fcn=self.plot_optimization_progress)

    def diamond_content_changed(self):
        new_value = float(str(self.main_widget.right_control_widget.diamond_widget.diamond_txt.text()))
        self.model.set_diamond_content(new_value)

    def optimize_diamond_btn_clicked(self):
        start_value = float(str(self.main_widget.right_control_widget.diamond_widget.diamond_txt.text()))

        def callback_fcn(diamond_content):
            self.main_widget.right_control_widget.diamond_widget.diamond_txt.setText('{:.2f}'.format(diamond_content))
            QtGui.QApplication.processEvents()

        self.model.optimize_diamond_content(diamond_content=start_value, callback_fcn=callback_fcn)

    def save_sq_btn_clicked(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getSaveFileName(self.main_widget, "Save S(Q) Data.",
                                                             os.path.join(self.sq_directory,
                                                                          self.model.original_pattern.name + ".txt"),
                                                             ('Data (*.txt)')))
        if filename is not '':
            self.model.sq_pattern.save(filename)
            self.sq_directory = os.path.dirname(filename)

    def save_gr_btn_clicked(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getSaveFileName(self.main_widget, "Save g(r) Data.",
                                                             os.path.join(self.gr_directory,
                                                                          self.model.original_pattern.name + ".txt"),
                                                             ('Data (*.txt)')))
        if filename is not '':
            self.model.gr_pattern.save(filename)
            self.gr_directory = os.path.dirname(filename)

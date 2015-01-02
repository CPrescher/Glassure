# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

__version__ = 0.1

import pyqtgraph as pg
# # Switch to using white background and black foreground
pg.setConfigOption('useOpenGL', False)
pg.setConfigOption('leftButtonPan', False)
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')
pg.setConfigOption('antialias', True)

from PyQt4 import QtGui, QtCore
import numpy as np
import os

from Views.MainWidget import MainWidget

from Models.GlassureModel import GlassureModel


class MainController(object):
    def __init__(self):
        self.main_widget = MainWidget()

        self.model = GlassureModel()
        self.model.subscribe(self.model_changed)
        self.working_directory = ''
        self.saving_directory = ''
        self.create_signals()
        self.main_widget.show()

    def create_signals(self):
        self.connect_click_function(self.main_widget.control_widget.data_widget.file_widget.load_data_btn, self.load_data)
        self.connect_click_function(self.main_widget.control_widget.data_widget.file_widget.load_background_btn, self.load_bkg)

        self.main_widget.control_widget.data_widget.background_options_gb.scale_sb.valueChanged.connect(self.bkg_scale_changed)
        self.main_widget.control_widget.data_widget.background_options_gb.offset_sb.valueChanged.connect(self.bkg_offset_changed)
        self.main_widget.control_widget.data_widget.smooth_gb.smooth_sb.valueChanged.connect(self.smooth_changed)

        self.connect_click_function(self.main_widget.control_widget.composition_widget.add_element_btn,
                                    self.add_element_btn_clicked)
        self.connect_click_function(self.main_widget.control_widget.composition_widget.delete_element_btn,
                                    self.delete_element_btn_clicked)

        self.main_widget.control_widget.composition_widget.composition_changed.connect(self.update_model)
        self.main_widget.control_widget.options_widget.options_parameters_changed.connect(self.update_model)
        self.main_widget.control_widget.optimization_widget.calculation_parameters_changed.connect(self.update_model)

        self.main_widget.control_widget.optimization_widget.optimize_btn.clicked.connect(self.optimize_btn_clicked)
        self.main_widget.control_widget.optimization_widget.optimize_density_btn.clicked.connect(self.optimize_density)

        self.connect_click_function(self.main_widget.spectrum_widget.mouse_position_widget.save_sq_btn,
                                    self.save_sq_btn_clicked)
        self.connect_click_function(self.main_widget.spectrum_widget.mouse_position_widget.save_pdf_btn,
                                    self.save_pdf_btn_clicked)

    def connect_click_function(self, emitter, function):
        self.main_widget.connect(emitter, QtCore.SIGNAL('clicked()'), function)

    def load_data(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(
                self.main_widget, caption="Load Spectrum", directory=self.working_directory))

        if filename is not '':
            self.model.load_data(filename)
            self.working_directory = os.path.dirname(filename)
            self.main_widget.control_widget.data_widget.file_widget.data_filename_lbl.setText(os.path.basename(filename))

    def load_bkg(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(self.main_widget, "Load background data",
                                                             directory=self.working_directory))

        if filename is not None and filename != '':
            self.model.load_bkg(filename)
            self.working_directory = os.path.dirname(filename)
            self.main_widget.control_widget.data_widget.file_widget.background_filename_lbl.setText(os.path.basename(filename))

    def model_changed(self):
        self.main_widget.spectrum_widget.plot_spectrum(self.model.original_spectrum)
        self.main_widget.spectrum_widget.plot_bkg(self.model.get_background_spectrum())
        self.main_widget.spectrum_widget.plot_sq(self.model.sq_spectrum)
        self.main_widget.spectrum_widget.plot_pdf(self.model.gr_spectrum)


    def bkg_scale_changed(self, value):
        self.model.set_bkg_scale(value)

    def bkg_offset_changed(self, value):
        self.model.set_bkg_offset(value)

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
        self.main_widget.control_widget.composition_widget.add_element(element="Si", value=1.0)

    def delete_element_btn_clicked(self):
        cur_ind = self.main_widget.control_widget.composition_widget.composition_tw.currentRow()
        self.main_widget.control_widget.composition_widget.delete_element(cur_ind)

    def update_model(self):
        composition = self.main_widget.control_widget.composition_widget.get_composition()
        density = self.main_widget.control_widget.composition_widget.get_density()

        q_min, q_max, r_min, r_max = self.main_widget.control_widget.options_widget.get_parameter()
        r_cutoff, _ = self.main_widget.control_widget.optimization_widget.get_parameter()

        use_modification_fcn = self.main_widget.control_widget.options_widget.modification_fcn_cb.isChecked()
        use_linear_interpolation = self.main_widget.control_widget.options_widget.linear_interpolation_cb.isChecked()

        self.model.update_parameter(composition, density,
                                    q_min, q_max,
                                    r_cutoff,
                                    r_min, r_max,
                                    use_modification_fcn,
                                    use_linear_interpolation)

    def optimize_btn_clicked(self):
        self.main_widget.control_widget.setEnabled(False)
        self.model.optimize_sq(
            iterations=int(str(self.main_widget.control_widget.optimization_widget.optimize_iterations_txt.text())),
            fcn_callback = self.plot_optimization_progress
        )
        self.main_widget.control_widget.setEnabled(True)

    def plot_optimization_progress(self, sq_spectrum, gr_spectrum):
        self.main_widget.spectrum_widget.plot_sq(sq_spectrum)
        self.main_widget.spectrum_widget.plot_pdf(gr_spectrum)
        QtGui.QApplication.processEvents()

    def optimize_density(self):
        self.model.optimize_density_and_scaling(
            iterations=int(str(self.main_widget.control_widget.optimization_widget.optimize_iterations_txt.text())))

    def save_sq_btn_clicked(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getSaveFileName(self.main_widget, "Save S(Q) Data.",
                                                             self.saving_directory,
                                                             ('Data (*.txt)')))
        if filename is not '':
            self.model.sq_spectrum.save(filename)
            self.saving_directory = os.path.dirname(filename)

    def save_pdf_btn_clicked(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getSaveFileName(self.main_widget, "Save g(r) Data.",
                                                             self.saving_directory,
                                                             ('Data (*.txt)')))
        if filename is not '':
            self.model.gr_spectrum.save(filename)
            self.saving_directory = os.path.dirname(filename)

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
        self.create_signals()
        self.raise_window()

    def create_signals(self):
        self.connect_click_function(self.main_widget.control_widget.file_widget.load_data_btn, self.load_data)
        self.connect_click_function(self.main_widget.control_widget.file_widget.load_background_btn, self.load_bkg)

        self.main_widget.control_widget.background_options_gb.scale_sb.valueChanged.connect(self.bkg_scale_changed)
        self.main_widget.control_widget.background_options_gb.offset_sb.valueChanged.connect(self.bkg_offset_changed)
        self.main_widget.control_widget.smooth_gb.smooth_sb.valueChanged.connect(self.smooth_changed)

        self.connect_click_function(self.main_widget.control_widget.composition_gb.add_element_btn,
                                    self.add_element_btn_clicked)
        self.connect_click_function(self.main_widget.control_widget.composition_gb.delete_element_btn,
                                    self.delete_element_btn_clicked)

        self.main_widget.control_widget.composition_gb.composition_changed.connect(self.update_model)
        self.main_widget.control_widget.calculation_gb.calculation_parameters_changed.connect(self.update_model)

        self.main_widget.control_widget.calculation_gb.optimize_btn.clicked.connect(self.optimize_btn_clicked)

    def connect_click_function(self, emitter, function):
        self.main_widget.connect(emitter, QtCore.SIGNAL('clicked()'), function)

    def load_data(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(
                self.main_widget, caption="Load Spectrum", directory=''))

        if filename is not '':
            self.model.load_data(filename)
            self.main_widget.control_widget.file_widget.data_filename_lbl.setText(os.path.basename(filename))

    def load_bkg(self, filename=None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(self.main_widget, "Load background data"))

        if filename is not None and filename != '':
            self.model.load_bkg(filename)
            self.main_widget.control_widget.file_widget.background_filename_lbl.setText(os.path.basename(filename))

    def model_changed(self):
        self.main_widget.spectrum_widget.plot_spectrum(self.model.original_spectrum)
        self.main_widget.spectrum_widget.plot_bkg(self.model.get_background_spectrum())
        self.main_widget.spectrum_widget.plot_sq(self.model.sq_spectrum)
        self.main_widget.spectrum_widget.plot_pdf(self.model.pdf_spectrum)

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
        self.main_widget.control_widget.composition_gb.add_element(element="Si", value=1.0)

    def delete_element_btn_clicked(self):
        cur_ind = self.main_widget.control_widget.composition_gb.composition_tw.currentRow()
        self.main_widget.control_widget.composition_gb.delete_element(cur_ind)

    def update_model(self):
        composition = self.main_widget.control_widget.composition_gb.get_composition()
        density = self.main_widget.control_widget.composition_gb.get_density()

        q_min, q_max, r_cutoff = self.main_widget.control_widget.calculation_gb.get_parameter()
        self.model.update_parameter(composition, density, q_min, q_max, r_cutoff)

    def optimize_btn_clicked(self):
        self.model.optimize_parameter()
        self.main_widget.control_widget.background_options_gb.scale_sb.setValue(self.model.background_scaling)
        self.main_widget.control_widget.composition_gb.density_txt.setText(str(self.model.density))

    def raise_window(self):
        self.main_widget.show()
        self.main_widget.setWindowState(
            self.main_widget.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.main_widget.activateWindow()
        self.main_widget.raise_()
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

from Views.MainWidget import MainWidget

from Models.GlassureModel import GlassureModel

class MainController(object):
    def __init__(self):
        self.view = MainWidget("Glassure {}".format(__version__)+u' - © 2014 C. Prescher')

        self.model = GlassureModel()
        self.model.subscribe(self.model_changed)
        self.create_signals()
        self.raise_window()

    def create_signals(self):
        self.connect_click_function(self.view.load_data_btn, self.load_data)
        self.connect_click_function(self.view.load_bkg_btn, self.load_bkg)

        self.view.bkg_scale_sb.valueChanged.connect(self.bkg_scale_changed)
        self.view.bkg_offset_sb.valueChanged.connect(self.bkg_offset_changed)
        self.view.bkg_scale_step_txt.editingFinished.connect(self.update_bkg_scale_step)
        self.view.bkg_offset_step_txt.editingFinished.connect(self.update_bkg_offset_step)

        self.view.smooth_sb.valueChanged.connect(self.smooth_changed)
        self.view.smooth_step_txt.editingFinished.connect(self.update_smooth_step)

        self.connect_click_function(self.view.add_element_btn, self.add_element_btn_clicked)
        self.connect_click_function(self.view.delete_element_btn, self.delete_element_btn_clicked)


    def connect_click_function(self, emitter, function):
        self.view.connect(emitter, QtCore.SIGNAL('clicked()'), function)

    def load_data(self, filename = None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(
                self.view, caption="Load Spectrum", directory = ''))

        if filename is not '':
            self.model.load_data(filename)

    def load_bkg(self, filename = None):
        if filename is None:
            filename = str(QtGui.QFileDialog.getOpenFileName(
                        self.view, "Load background data"))

        if filename is not None and filename != '':
            self.model.load_bkg(filename)

    def model_changed(self):
        x, y = self.model.original_spectrum.data
        self.view.spectrum_widget.plot_data(x,y)

    def bkg_scale_changed(self, value):
        self.model.set_bkg_scale(value)

    def bkg_offset_changed(self, value):
        self.model.set_bkg_offset(value)

    def update_bkg_scale_step(self):
        value = np.float(self.view.bkg_scale_step_txt.text())
        self.view.bkg_scale_sb.setSingleStep(value)

    def update_bkg_offset_step(self):
        value = np.float(self.view.bkg_offset_step_txt.text())
        self.view.bkg_offset_sb.setSingleStep(value)

    def smooth_changed(self, value):
        self.model.set_smooth(value)

    def update_smooth_step(self):
        value = np.float(self.view.smooth_step_txt.text())
        self.view.smooth_sb.setSingleStep(value)

    def add_element_btn_clicked(self):
        self.view.add_element_to_composition_tw(element = "Si", value = 1.0)

    def delete_element_btn_clicked(self):
        pass

    def raise_window(self):
        self.view.show()
        self.view.setWindowState(self.view.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.view.activateWindow()
        self.view.raise_()
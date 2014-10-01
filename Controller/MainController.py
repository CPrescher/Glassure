# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import pyqtgraph as pg
# # Switch to using white background and black foreground
pg.setConfigOption('useOpenGL', False)
pg.setConfigOption('leftButtonPan', False)
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')
pg.setConfigOption('antialias', True)

from PyQt4 import QtGui, QtCore

from Views.MainWidget import MainWidget

from Models.GlassureModel import GlassureModel

class MainController(object):
    def __init__(self):
        self.view = MainWidget()

        self.model = GlassureModel()
        self.model.subscribe(self.model_changed)
        self.create_signals()
        self.raise_window()

    def create_signals(self):
        self.connect_click_function(self.view.load_data_btn, self.load_data)
        self.connect_click_function(self.view.load_bkg_btn, self.load_bkg)


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

    def raise_window(self):
        self.view.show()
        self.view.setWindowState(self.view.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.view.activateWindow()
        self.view.raise_()
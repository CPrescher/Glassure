# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtGui, QtCore

from UiFiles.MainUI import Ui_MainWidget

from .SpectrumWidget import SpectrumWidget

class MainWidget(QtGui.QWidget,Ui_MainWidget):

    def __init__(self):
        super(MainWidget, self).__init__(None)
        self.setupUi(self)

        self.spectrum_widget = SpectrumWidget(self.spectrum_pg_layout, 'Q(A<sup>-1</sup>)', 'Intensity')
        self.set_validators()

    def set_validators(self):
        self.bkg_scale_step_txt.setValidator(QtGui.QDoubleValidator())
        self.bkg_offset_step_txt.setValidator(QtGui.QDoubleValidator())
        self.smooth_step_txt.setValidator(QtGui.QDoubleValidator())
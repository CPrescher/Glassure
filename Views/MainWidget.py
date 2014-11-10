# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtGui, QtCore

from UiFiles.MainUI import Ui_MainWidget
from .SpectrumWidget import SpectrumWidget

from ScatteringFactors import scattering_factor_param


class MainWidget(QtGui.QWidget,Ui_MainWidget):

    def __init__(self, title=''):
        super(MainWidget, self).__init__(None)
        self.setupUi(self)
        self.setWindowTitle(title)
        self.spectrum_widget = SpectrumWidget(self.spectrum_pg_layout)
        self.set_validators()

        self.element_cbs = []

    def set_validators(self):
        self.bkg_scale_step_txt.setValidator(QtGui.QDoubleValidator())
        self.bkg_offset_step_txt.setValidator(QtGui.QDoubleValidator())
        self.smooth_step_txt.setValidator(QtGui.QDoubleValidator())

    def add_element_to_composition_tw(self, element, value):
        current_rows = self.composition_tw.rowCount()
        self.composition_tw.setRowCount(current_rows+1)
        self.composition_tw.blockSignals(True)

        element_cb = QtGui.QComboBox(self)
        element_cb.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
        for ind, element in enumerate(scattering_factor_param.index):
            element_cb.insertItem(ind, element)
        self.composition_tw.setCellWidget(current_rows,0, element_cb)

        value_item = QtGui.QTableWidgetItem(str(value))
        value_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.composition_tw.setItem(current_rows, 1, value_item)

        self.composition_tw.blockSignals(False)

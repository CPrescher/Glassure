# -*- coding: utf8 -*-
import os

from ..qt import QtCore, QtGui

from ..widgets.glassure import GlassureWidget
from ..model.glassure import GlassureModel


class TransferFunctionController(object):
    def __init__(self, widget, glassure_model):
        """
        :param widget:
        :type widget: GlassureWidget
        :param glassure_model:
        :type glassure_model: GlassureModel
        """

        self.widget = widget
        self.transfer_widget = widget.transfer_widget
        self.model = glassure_model

        self.connect_signals()

    def connect_signals(self):
        self.transfer_widget.activate_cb.stateChanged.connect(self.active_cb_state_changed)

        self.transfer_widget.load_sample_btn.clicked.connect(self.load_sample_pattern)
        self.transfer_widget.load_sample_bkg_btn.clicked.connect(self.load_sample_bkg_pattern)
        self.transfer_widget.load_std_btn.clicked.connect(self.load_std_pattern)
        self.transfer_widget.load_std_bkg_btn.clicked.connect(self.load_std_bkg_pattern)

        self.transfer_widget.sample_bkg_scaling_sb.valueChanged.connect(self.sample_bkg_scaling_changed)
        self.transfer_widget.std_bkg_scaling_sb.valueChanged.connect(self.std_bkg_scaling_changed)
        self.transfer_widget.smooth_sb.valueChanged.connect(self.smooth_factor_changed)

    def load_sample_pattern(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self.widget,
                                                         caption="Load Sample Spectrum (in Container)"))

        if filename is not '':
            self.model.load_transfer_sample_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.sample_filename_lbl.setText(os.path.basename(filename))

    def load_sample_bkg_pattern(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self.widget,
                                                         caption="Load Sample Spectrum (in Container)"))

        if filename is not '':
            self.model.load_transfer_sample_bkg_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.sample_bkg_filename_lbl.setText(os.path.basename(filename))

    def load_std_pattern(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self.widget,
                                                         caption="Load Sample Spectrum (in Container)"))

        if filename is not '':
            self.model.load_transfer_std_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.std_filename_lbl.setText(os.path.basename(filename))

    def load_std_bkg_pattern(self):
        filename = str(QtGui.QFileDialog.getOpenFileName(self.widget,
                                                         caption="Load Sample Spectrum (in Container)"))

        if filename is not '':
            self.model.load_transfer_std_bkg_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.std_bkg_filename_lbl.setText(os.path.basename(filename))

    def active_cb_state_changed(self):
        self.model.use_transfer_function = self.transfer_widget.activate_cb.isChecked()

    def sample_bkg_scaling_changed(self, new_value):
        self.model.transfer_sample_bkg_scaling = float(new_value)

    def std_bkg_scaling_changed(self, new_value):
        self.model.transfer_std_bkg_scaling = float(new_value)

    def smooth_factor_changed(self, new_value):
        self.model.transfer_function_smoothing = new_value

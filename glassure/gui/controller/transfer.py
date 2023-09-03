# -*- coding: utf-8 -*-
import os

from qtpy import QtCore

from ..widgets.glassure_widget import GlassureWidget
from ..widgets.custom.file_dialogs import open_file_dialog
from ..model.glassure_model import GlassureModel


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
        self.settings = QtCore.QSettings('Glassure', 'Glassure')

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
        filename = open_file_dialog(self.widget, caption="Load Sample Pattern (in Container)",
                                    directory=self.settings.value('working_directory'))

        if filename != '':
            self.model.load_transfer_sample_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.sample_filename_lbl.setText(os.path.basename(filename))

    def load_sample_bkg_pattern(self):
        filename = open_file_dialog(self.widget, caption="Load Sample background Pattern (in Container)",
                                    directory=self.settings.value('working_directory'))

        if filename != '':
            self.model.load_transfer_sample_bkg_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.sample_bkg_filename_lbl.setText(os.path.basename(filename))

    def load_std_pattern(self):
        filename = open_file_dialog(self.widget, caption="Load Standard Pattern (in Container)",
                                    directory=self.settings.value('working_directory'))

        if filename != '':
            self.model.load_transfer_std_pattern(filename)
            self.working_directory = os.path.dirname(filename)
            self.transfer_widget.std_filename_lbl.setText(os.path.basename(filename))

    def load_std_bkg_pattern(self):
        filename = open_file_dialog(self.widget, caption="Load Standard Background Pattern (in Container)",
                                    directory=self.settings.value('working_directory'))

        if filename != '':
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

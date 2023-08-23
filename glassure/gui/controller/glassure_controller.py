# -*- coding: utf-8 -*-

import os

from PySide6.QtCore import Slot
from qtpy import QtCore, QtWidgets
import pyqtgraph as pg

from ..widgets.glassure_widget import GlassureWidget
from ..widgets.custom.file_dialogs import open_file_dialog, save_file_dialog

from ..model.glassure_model import GlassureModel
from ...core.scattering_factors import get_available_elements

from .configuration import ConfigurationController
from .soller import SollerController
from .transfer import TransferFunctionController

# # Switch to using black background and white foreground
pg.setConfigOption('useOpenGL', False)
pg.setConfigOption('leftButtonPan', False)
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')
pg.setConfigOption('antialias', True)


class GlassureController(object):
    def __init__(self):
        self.main_widget = GlassureWidget()

        self.model = GlassureModel()
        self.settings = QtCore.QSettings('Glassure', 'Glassure')
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

        self.main_widget.load_data_btn.clicked.connect(self.load_data)
        self.main_widget.load_bkg_btn.clicked.connect(self.load_bkg)
        self.main_widget.reset_bkg_btn.clicked.connect(self.reset_bkg)

        # connecting background scaling and smoothing of the original data
        self.main_widget.bkg_scaling_sb.valueChanged.connect(self.bkg_scale_changed)
        self.main_widget.smooth_sb.valueChanged.connect(self.smooth_changed)

        # updating the composition
        self.main_widget.left_control_widget.composition_widget.source_cb.currentTextChanged.connect(
            self.data_source_changed)
        self.main_widget.add_element_btn.clicked.connect(self.add_element_btn_clicked)
        self.main_widget.delete_element_btn.clicked.connect(self.delete_element_btn_clicked)
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
        self.main_widget.save_sq_btn.clicked.connect(self.save_sq_btn_clicked)
        self.main_widget.save_gr_btn.clicked.connect(self.save_gr_btn_clicked)

    def load_data(self):
        filename = open_file_dialog(self.main_widget, caption="Load Pattern",
                                    directory=self.settings.value('working_directory'))

        if filename != '':
            self.model.load_data(filename)
            self.settings.setValue('working_directory', os.path.dirname(filename))
            self.main_widget.left_control_widget.data_widget.file_widget.data_filename_lbl.setText(
                self.model.current_configuration.original_pattern.name)

    def load_bkg(self):
        filename = open_file_dialog(self.main_widget, "Load background data",
                                    directory=self.settings.value('working_directory'))

        if filename is not None and filename != '':
            self.model.load_bkg(filename)
            self.settings.setValue('working_directory', os.path.dirname(filename))
            self.main_widget.left_control_widget.data_widget.file_widget.background_filename_lbl.setText(
                self.model.current_configuration.background_pattern.name)
    
    def reset_bkg(self):
        self.model.reset_bkg()

    def model_changed(self):
        if self.model.original_pattern is not None:
            self.main_widget.pattern_widget.plot_pattern(self.model.original_pattern)
        self.main_widget.pattern_widget.plot_bkg(self.model.background_pattern)
        if self.model.sq_pattern is not None:
            self.main_widget.pattern_widget.set_sq_pattern(self.model.sq_pattern, self.model.configuration_ind)
        if self.model.gr_pattern is not None:
            self.main_widget.pattern_widget.set_gr_pattern(self.model.gr_pattern, self.model.configuration_ind)

        if self.model.background_pattern is not None:
            self.main_widget.bkg_filename_lbl.setText(self.model.background_pattern.name)
            self.main_widget.bkg_scaling_sb.setEnabled(True)
            self.main_widget.bkg_scaling_sb.setValue(self.model.background_pattern.scaling)
        else:
            self.main_widget.bkg_filename_lbl.setText('None')
            self.main_widget.bkg_scaling_sb.setEnabled(False)

        self.main_widget.smooth_sb.setValue(self.model.original_pattern.smoothing)
        self.main_widget.left_control_widget.composition_widget.density_atomic_units_lbl. \
            setText("{:.4f}".format(self.model.atomic_density))

    def bkg_scale_changed(self, value):
        self.model.background_scaling = value

    def update_bkg_scale_step(self):
        value = float(self.main_widget.bkg_scale_step_txt.text())
        self.main_widget.bkg_scale_sb.setSingleStep(value)

    def update_bkg_offset_step(self):
        value = float(self.main_widget.bkg_offset_step_txt.text())
        self.main_widget.bkg_offset_sb.setSingleStep(value)

    def smooth_changed(self, value):
        self.model.set_smooth(value)

    def update_smooth_step(self):
        value = float(self.main_widget.smooth_step_txt.text())
        self.main_widget.smooth_sb.setSingleStep(value)

    def add_element_btn_clicked(self):
        self.main_widget.left_control_widget.composition_widget.add_element(element="Si", value=1.0)

    def delete_element_btn_clicked(self):
        cur_ind = self.main_widget.left_control_widget.composition_widget.composition_tw.currentRow()
        self.main_widget.left_control_widget.composition_widget.delete_element(cur_ind)

    def data_source_changed(self, source: str):
        self.validate_composition(source)
        self.update_model()

    def validate_composition(self, source):
        composition = self.main_widget.get_composition()
        for element in list(composition.keys()):
            if element not in get_available_elements(source):
                del composition[element]
        self.main_widget.left_control_widget.composition_widget.set_composition(composition)

    @Slot()
    def update_model(self):
        composition = self.main_widget.get_composition()
        sf_source = self.main_widget.get_sf_source()

        density = self.main_widget.left_control_widget.composition_widget.get_density()

        q_min, q_max, r_min, r_max = self.main_widget.get_parameter()

        use_modification_fcn = self.main_widget.use_modification_cb.isChecked()
        extrapolation_method = self.main_widget.get_extrapolation_method()
        extrapolation_parameters = self.main_widget.get_extrapolation_parameters()

        optimize_active, r_cutoff, optimize_iterations, optimize_attenuation = \
            self.main_widget.get_optimization_parameter()

        self.model.update_parameter(sf_source,
                                    composition, density,
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

    def plot_optimization_progress(self, sq_pattern, fr_pattern, gr_pattern):
        self.main_widget.pattern_widget.set_sq_pattern(sq_pattern, self.model.configuration_ind)
        self.main_widget.pattern_widget.set_gr_pattern(gr_pattern, self.model.configuration_ind)
        QtWidgets.QApplication.processEvents()

    def optimize_density(self):
        density_min, density_max, bkg_min, bkg_max, iterations = \
            self.main_widget.right_control_widget.density_optimization_widget.get_parameters()
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
            QtWidgets.QApplication.processEvents()

        self.model.optimize_diamond_content(diamond_content=start_value, callback_fcn=callback_fcn)

    def save_sq_btn_clicked(self):
        if self.settings.value('sq_directory') is not None:
            sq_filename = os.path.join(self.settings.value('sq_directory'),
                                       self.model.original_pattern.name + ".txt")
        else:
            sq_filename = None
        filename = save_file_dialog(self.main_widget,
                                    "Save S(Q) Data.",
                                    sq_filename,
                                    ('Data (*.txt)'))
        if filename != '':
            self.model.sq_pattern.save(filename)
            self.settings.setValue('sq_directory', os.path.dirname(filename))

    def save_gr_btn_clicked(self):
        if self.settings.value('gr_directory') is not None:
            gr_filename = os.path.join(self.settings.value('gr_directory'),
                                       self.model.original_pattern.name + ".txt")
        else:
            gr_filename = None
        filename = save_file_dialog(self.main_widget,
                                    "Save g(r) Data.",
                                    gr_filename,
                                    ('Data (*.txt)'))
        if filename != '':
            self.model.gr_pattern.save(filename)
            self.settings.setValue('gr_directory', os.path.dirname(filename))

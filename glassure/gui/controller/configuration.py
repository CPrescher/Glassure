# -*- coding: utf-8 -*-

import os
from qtpy import QtGui, QtWidgets, QtCore

from ..widgets.glassure_widget import GlassureWidget
from ..model.glassure_model import GlassureModel
from ..widgets.custom.file_dialogs import save_file_dialog, open_file_dialog


class ConfigurationController(object):
    def __init__(self, main_widget: GlassureWidget,
                 glassure_model: GlassureModel):
        """
        :param main_widget:
        :param glassure_model:
        """

        self.widget = main_widget
        self.model = glassure_model
        self.settings = QtCore.QSettings('Glassure', 'Glassure')

        self.connect_signals()

        self.update_configurations_tw()
        self.update_widget_controls()

    def connect_signals(self):
        self.widget.freeze_configuration_btn.clicked.connect(self.model.add_configuration)
        self.widget.remove_configuration_btn.clicked.connect(self.model.remove_configuration)
        self.widget.configuration_tw.currentCellChanged.connect(self.model.select_configuration)

        self.model.configurations_changed.connect(self.update_configurations_tw)
        self.model.configurations_changed.connect(self.update_pattern_items)
        self.model.configurations_changed.connect(self.update_widget_controls)

        self.model.configuration_selected.connect(self.update_widget_controls)
        self.model.configuration_selected.connect(self.update_pattern_items)

        self.widget.configuration_widget.configuration_show_cb_state_changed.connect(
            self.update_configuration_visibility)
        self.widget.configuration_widget.configuration_color_btn_clicked.connect(self.configuration_color_btn_clicked)
        self.widget.configuration_widget.configuration_name_changed.connect(self.update_configuration_name)
        self.widget.configuration_widget.save_btn.clicked.connect(self.save_model)
        self.widget.configuration_widget.load_btn.clicked.connect(self.load_model)

    def freeze_configuration(self):
        """
        Callback for the freeze configuration button. Adds a new configuration
        to the model with the current settings. (i.e. duplicates the current
        configuration)
        """
        self.model.add_configuration()

    def update_configurations_tw(self):
        """Updates the configuration table widget"""
        self.widget.configuration_tw.blockSignals(True)
        self.widget.configuration_widget.clear_configuration_tw()

        for configuration in self.model.configurations:
            color = configuration.color
            self.widget.configuration_widget.add_configuration(
                configuration.name,
                '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2])),
                show=configuration.show
            )
        self.widget.configuration_tw.blockSignals(False)
        self.widget.configuration_widget.select_configuration(self.model.configuration_ind)

    def update_widget_controls(self):
        self.widget.right_control_widget.optimization_widget.blockSignals(True)

        # filenames
        self.widget.data_filename_lbl.setText(self.model.original_pattern.name)
        if self.model.current_configuration.background_pattern is not None:
            self.widget.bkg_filename_lbl.setText(self.model.current_configuration.background_pattern.name)
            self.widget.bkg_scaling_sb.setEnabled(True)
            self.widget.bkg_scaling_sb.setValue(self.model.current_configuration.background_pattern.scaling)
        else:
            self.widget.bkg_filename_lbl.setText('None')
            self.widget.bkg_scaling_sb.setEnabled(False)
        self.widget.smooth_sb.setValue(self.model.original_pattern.smoothing)

        self.widget.update_sample_config(self.model.sample)
        self.widget.update_transform_config(self.model.transform_config)
        self.widget.left_control_widget.extrapolation_widget.update_configuration(self.model.extrapolation_config)

        # optimizations widget
        self.widget.optimize_activate_cb.setChecked(self.model.optimize)
        self.widget.set_optimization_parameter(self.model.r_cutoff,
                                               self.model.optimization_iterations,
                                               self.model.optimization_attenuation)
        self.widget.right_control_widget.optimization_widget.blockSignals(False)

        # soller widget
        self.widget.soller_active_cb.setChecked(self.model.use_soller_correction)
        self.widget.set_soller_parameter(self.model.soller_parameters)

    def update_pattern_items(self):
        self.update_data_plot()
        self.update_plot_item_count(len(self.model.configurations))
        self.update_pattern_items_data(self.model.configuration_ind)
        self.update_pattern_items_color(self.model.configuration_ind)

    def update_data_plot(self):
        self.widget.pattern_widget.plot_pattern(self.model.original_pattern)
        self.widget.pattern_widget.plot_bkg(self.model.background_pattern)

    def update_plot_item_count(self, count):
        """ Updates the number of plot items in the sq-plot and the gr-plot """

        for i in range(len(self.widget.pattern_widget.sq_items), count):
            self.widget.pattern_widget.add_sq_item(show=self.model.configurations[i].show)
            self.widget.pattern_widget.add_gr_item(show=self.model.configurations[i].show)

        while len(self.widget.pattern_widget.sq_items) > count:
            self.widget.pattern_widget.remove_sq_item()
            self.widget.pattern_widget.remove_gr_item()

    def update_pattern_items_data(self, cur_ind):
        for ind in range(len(self.model.configurations)):
            if self.model.configurations[ind].sq_pattern is None:
                continue
            self.widget.pattern_widget.set_sq_pattern(self.model.configurations[ind].sq_pattern, ind)
            self.widget.pattern_widget.set_gr_pattern(self.model.configurations[ind].gr_pattern, ind)

    def update_pattern_items_color(self, cur_ind):
        for ind in range(len(self.model.configurations)):
            if ind == self.model.configuration_ind:
                self.widget.pattern_widget.activate_ind(ind)
            else:
                self.widget.pattern_widget.set_color(self.model.configurations[ind].color, ind)

    def update_configuration_visibility(self, ind, visible):
        self.model.configurations[ind].show = visible
        if visible:
            self.widget.pattern_widget.show_sq(ind)
            self.widget.pattern_widget.show_gr(ind)
        else:
            self.widget.pattern_widget.hide_sq(ind)
            self.widget.pattern_widget.hide_gr(ind)

    def configuration_color_btn_clicked(self, ind, button):
        """
        Callback for the color buttons in the configuration table. Opens up a
        color dialog. The color of the configuration and its respective button
        will be changed according to the selection

        :param ind: configuration ind
        :param button: button to color
        """
        previous_color = button.palette().color(QtGui.QPalette.Button)
        new_color = QtWidgets.QColorDialog.getColor(previous_color, self.widget)

        if not new_color.isValid():
            return

        self.model.configurations[ind].color = [new_color.red(), new_color.green(), new_color.blue()]
        self.update_pattern_items_color(self.model.configuration_ind)
        button.setStyleSheet('background-color:' + new_color.name())

    def update_configuration_name(self, ind, name):
        self.model.configurations[ind].name = name

    def save_model(self):
        filename = save_file_dialog(
            self.widget,
            'Save model',
            self.settings.value('working_directory'),
            filter='*.json')
        if filename == '':
            return
        self.settings.setValue('working_directory', os.path.dirname(filename))
        self.model.to_json(filename)

    def load_model(self):
        filename = open_file_dialog(
            self.widget,
            'Load model',
            self.settings.value('working_directory'),
            filter='*.json')
        if filename == '':
            return
        self.settings.setValue('working_directory', os.path.dirname(filename))
        self.model.read_json(filename)

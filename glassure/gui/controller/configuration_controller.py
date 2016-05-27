# -*- coding: utf8 -*-

from ..qt import QtGui

from ..widgets.glassure_widget import GlassureWidget
from ..model.glassure_model import GlassureModel


class ConfigurationController(object):
    def __init__(self, main_widget, glassure_model):
        """
        :param main_widget:
        :type main_widget: GlassureWidget
        :param glassure_model:
        :type glassure_model: GlassureModel
        """

        self.main_widget = main_widget
        self.model = glassure_model

        self.connect_signals()

        self.update_configurations_tw()

    def connect_signals(self):
        self.main_widget.freeze_configuration_btn.clicked.connect(self.model.add_configuration)
        self.main_widget.remove_configuration_btn.clicked.connect(self.model.remove_configuration)
        self.main_widget.configuration_tw.currentCellChanged.connect(self.model.select_configuration)

        self.model.configurations_changed.connect(self.update_configurations_tw)
        self.model.configurations_changed.connect(self.update_spectrum_items)

        self.model.configuration_selected.connect(self.update_widget_controls)
        self.model.configuration_selected.connect(self.update_spectrum_items)

        self.main_widget.configuration_widget.configuration_show_cb_state_changed.connect(
            self.update_configuration_visibility
        )
        self.main_widget.configuration_widget.configuration_color_btn_clicked.connect(
            self.configuration_color_btn_clicked
        )

    def freeze_configuration(self):
        self.model.add_configuration()

    def update_configurations_tw(self):
        self.main_widget.configuration_tw.blockSignals(True)
        self.main_widget.configuration_widget.clear_configuration_tw()

        for configuration in self.model.configurations:
            color = configuration.color
            self.main_widget.configuration_widget.add_configuration(
                configuration.name,
                '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2]))
            )
        self.main_widget.configuration_tw.blockSignals(False)
        self.main_widget.configuration_widget.select_configuration(self.model.configuration_ind)

    def update_widget_controls(self):
        self.main_widget.right_control_widget.optimization_widget.blockSignals(True)

        # filenames
        self.main_widget.data_filename_lbl.setText(self.model.original_pattern.name)
        self.main_widget.bkg_filename_lbl.setText(self.model.current_configuration.background_pattern.name)

        # background scaling and smoothing
        self.main_widget.bkg_scaling_sb.setValue(self.model.current_configuration.background_pattern.scaling)
        self.main_widget.smooth_sb.setValue(self.model.original_pattern.smoothing)

        # composition widget
        self.main_widget.set_composition(self.model.composition)
        self.main_widget.density_txt.setText(str(self.model.density))

        # parameters widget
        self.main_widget.q_min_txt.setText(str(self.model.q_min))
        self.main_widget.q_max_txt.setText(str(self.model.q_max))

        self.main_widget.r_min_txt.setText(str(self.model.r_min))
        self.main_widget.r_max_txt.setText(str(self.model.r_max))

        self.main_widget.use_modification_cb.setChecked(self.model.use_modification_fcn)

        # extrapolations widget
        self.main_widget.set_extrapolation_method(self.model.extrapolation_method)
        if self.model.extrapolation_method in ('poly', 'spline'):
            self.main_widget.set_extrapolation_parameters(self.model.extrapolation_parameters)

        # optimizations widget
        self.main_widget.optimize_activate_cb.setChecked(self.model.optimize)
        self.main_widget.set_optimization_parameter(self.model.r_cutoff, self.model.optimization_iterations,
                                                    self.model.optimization_attenuation)
        self.main_widget.right_control_widget.optimization_widget.blockSignals(False)

    def update_spectrum_items(self):
        while len(self.main_widget.spectrum_widget.sq_items) < len(self.model.configurations):
            self.main_widget.spectrum_widget.add_sq_item()
            self.main_widget.spectrum_widget.add_gr_item()

        while len(self.main_widget.spectrum_widget.sq_items) > len(self.model.configurations):
            self.main_widget.spectrum_widget.remove_sq_item()
            self.main_widget.spectrum_widget.remove_gr_item()

        self.update_spectrum_items_data(self.model.configuration_ind)
        self.update_spectrum_items_color(self.model.configuration_ind)

    def update_spectrum_items_data(self, cur_ind):
        for ind in range(len(self.model.configurations)):
            if self.model.configurations[ind].sq_pattern is None:
                continue
            self.main_widget.spectrum_widget.set_sq_pattern(self.model.configurations[ind].sq_pattern, ind)
            self.main_widget.spectrum_widget.set_gr_pattern(self.model.configurations[ind].gr_pattern, ind)

    def update_spectrum_items_color(self, cur_ind):
        for ind in range(len(self.model.configurations)):
            if ind == self.model.configuration_ind:
                self.main_widget.spectrum_widget.activate_ind(ind)
            else:
                self.main_widget.spectrum_widget.set_color(self.model.configurations[ind].color, ind)

    def update_configuration_visibility(self, ind, visible):
        if visible:
            self.main_widget.spectrum_widget.show_sq(ind)
            self.main_widget.spectrum_widget.show_gr(ind)
        else:
            self.main_widget.spectrum_widget.hide_sq(ind)
            self.main_widget.spectrum_widget.hide_gr(ind)

    def configuration_color_btn_clicked(self, ind, button):
        """
        Callback for the color buttons in the configuration table. Opens up a color dialog. The color of the
        configuration and its respective button will be changed according to the selection
        :param ind: configuration ind
        :param button: button to color
        """
        previous_color = button.palette().color(1)
        new_color = QtGui.QColorDialog.getColor(previous_color, self.main_widget)

        if not new_color.isValid():
            return

        self.model.configurations[ind].color = [new_color.red(), new_color.green(), new_color.blue()]
        self.update_spectrum_items_color(self.model.configuration_ind)
        button.setStyleSheet('background-color:' + new_color.name())

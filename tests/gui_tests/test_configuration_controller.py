# -*- coding: utf-8 -*-
from mock import MagicMock
from qtpy import QtGui, QtWidgets

from .utility import set_widget_text, click_checkbox, click_button


def test_data_filename_is_updated(main_controller, main_widget, configuration_widget, configuration_controller, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_controller.model.original_pattern.name = 'lala'

    configuration_controller.update_widget_controls()
    assert str(main_widget.data_filename_lbl.text()) == 'lala'

    configuration_widget.configuration_tw.selectRow(0)
    assert str(main_widget.data_filename_lbl.text()) == ''


def test_bkg_filename_is_updated(main_controller, main_widget, configuration_widget, configuration_controller, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_controller.model.current_configuration.background_pattern.name = 'lala'

    configuration_controller.update_widget_controls()
    assert str(main_widget.bkg_filename_lbl.text()) == 'lala'

    configuration_widget.configuration_tw.selectRow(0)
    assert str(main_widget.bkg_filename_lbl.text()) == ''


def test_bkg_scaling_is_updated(main_controller, main_widget, configuration_widget, configuration_controller, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_widget.bkg_scaling_sb.setValue(0.3)

    configuration_controller.update_widget_controls()
    assert main_widget.bkg_scaling_sb.value() == 0.3

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.bkg_scaling_sb.value() == 1


def test_smooth_factor_is_updated(main_controller, main_widget, configuration_widget, configuration_controller, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_widget.smooth_sb.setValue(4)

    configuration_controller.update_widget_controls()
    assert main_widget.smooth_sb.value() == 4

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.smooth_sb.value() == 0


def test_composition_is_updated(main_controller, main_widget, configuration_widget, configuration_controller, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_controller.model.current_configuration.composition = {'Fe': 0.5, 'Ni': 0.5}

    configuration_controller.update_widget_controls()
    assert main_widget.composition_tw.rowCount() == 2

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.composition_tw.rowCount() == 0


# base tests for testing text widgets
def txt_widget_update_test(test_widget, value, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    prev_value = float(str(test_widget.text()))
    set_widget_text(test_widget, value)

    configuration_widget.configuration_tw.selectRow(0)
    assert float(str(test_widget.text())) == prev_value

    configuration_widget.configuration_tw.selectRow(1)
    assert float(str(test_widget.text())) == value


def test_density_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.density_txt, 2.9, configuration_widget)


def test_q_min_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.q_min_txt, 2, configuration_widget)


def test_q_max_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.q_max_txt, 9, configuration_widget)


def test_r_min_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.r_min_txt, 0.1, configuration_widget)


def test_r_max_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.r_max_txt, 9.5, configuration_widget)


def test_r_cutoff_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.optimize_r_cutoff_txt, 5, configuration_widget)


def test_optimization_iterations_is_updated(main_widget, configuration_widget):
    txt_widget_update_test(main_widget.optimize_iterations_txt, 3, configuration_widget)


def test_use_modification_function_is_updated(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    click_checkbox(main_widget.use_modification_cb)

    configuration_widget.configuration_tw.selectRow(0)
    assert not main_widget.use_modification_cb.isChecked()

    configuration_widget.configuration_tw.selectRow(1)
    assert main_widget.use_modification_cb.isChecked()


def test_extrapolation_method_is_updated(main_widget, configuration_widget, extrapolation_widget):
    click_button(configuration_widget.freeze_btn)
    click_checkbox(extrapolation_widget.linear_extrapolation_rb)
    click_button(configuration_widget.freeze_btn)
    click_checkbox(main_widget.activate_extrapolation_cb)  # deactivate

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.activate_extrapolation_cb.isChecked()
    assert extrapolation_widget.step_extrapolation_rb.isChecked()


def test_configuration_parameters_are_updated(main_widget, configuration_widget, extrapolation_widget):
    click_checkbox(extrapolation_widget.poly_extrapolation_rb)
    click_button(configuration_widget.freeze_btn)

    set_widget_text(extrapolation_widget.q_max_txt, 1.4)
    click_checkbox(extrapolation_widget.replace_cb)

    configuration_widget.configuration_tw.selectRow(0)
    assert float(str(extrapolation_widget.q_max_txt.text())) == 2
    assert not extrapolation_widget.replace_cb.isChecked()

    configuration_widget.configuration_tw.selectRow(1)
    assert float(str(extrapolation_widget.q_max_txt.text())) == 1.4
    assert extrapolation_widget.replace_cb.isChecked()


def test_optimization_activate_is_updated(main_widget, configuration_widget):
    activate_cb = main_widget.optimize_activate_cb
    click_button(configuration_widget.freeze_btn)
    click_checkbox(activate_cb)
    click_button(configuration_widget.freeze_btn)

    assert activate_cb.isChecked()

    configuration_widget.configuration_tw.selectRow(0)
    assert not activate_cb.isChecked()


def test_optimization_attenuation_is_updated(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    main_widget.optimize_attenuation_sb.setValue(4)

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.optimize_attenuation_sb.value() == 1

    configuration_widget.configuration_tw.selectRow(1)
    assert main_widget.optimize_attenuation_sb.value() == 4


def test_soller_parameters_are_updated(main_widget, configuration_widget, qtbot):
    click_button(configuration_widget.freeze_btn)
    main_widget.right_control_widget.soller_widget.wavelength_txt.set_value(0.3344)
    main_widget.right_control_widget.soller_widget.wavelength_txt.editingFinished.emit()

    configuration_widget.configuration_tw.selectRow(0)
    assert main_widget.right_control_widget.soller_widget.wavelength_txt.get_value() == 0.31

    configuration_widget.configuration_tw.selectRow(1)
    assert main_widget.right_control_widget.soller_widget.wavelength_txt.get_value() == 0.3344


def test_soller_parameters_stress_test(configuration_widget, main_widget, model):
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)

    soller_parameters1 = main_widget.soller_widget.get_parameters()

    soller_parameters2 = {'sample_thickness': 2.0,  # in mm
                          'wavelength': 0.3,  # in Angstrom
                          'inner_radius': 61,  # in mm
                          'outer_radius': 220,  # in mm
                          'inner_width': 0.01,  # in mm
                          'outer_width': 0.3,  # in mm
                          'inner_length': 2,  # in mm
                          'outer_length': 4}  # in mm

    soller_parameters3 = {'sample_thickness': 1.5,  # in mm
                          'wavelength': 0.1,  # in Angstrom
                          'inner_radius': 34,  # in mm
                          'outer_radius': 212,  # in mm
                          'inner_width': 0.123,  # in mm
                          'outer_width': 0.32,  # in mm
                          'inner_length': 4,  # in mm
                          'outer_length': 5}  # in mm

    configuration_widget.configuration_tw.selectRow(1)
    model.soller_parameters = soller_parameters2
    configuration_widget.configuration_tw.selectRow(2)
    model.soller_parameters = soller_parameters3

    configuration_widget.configuration_tw.selectRow(0)
    assert soller_parameters1 == main_widget.soller_widget.get_parameters()
    configuration_widget.configuration_tw.selectRow(1)
    assert soller_parameters2 == main_widget.soller_widget.get_parameters()
    configuration_widget.configuration_tw.selectRow(2)
    assert soller_parameters3 == main_widget.soller_widget.get_parameters()


def test_new_plots_are_created(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    assert len(main_widget.pattern_widget.gr_items) == 2


def test_plot_items_are_removed(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.remove_btn)
    assert len(main_widget.pattern_widget.gr_items) == 2


def test_plot_items_show_different_data(main_widget, configuration_widget):
    click_button(main_widget.add_element_btn)
    click_button(configuration_widget.freeze_btn)
    set_widget_text(main_widget.q_max_txt, 12)

    x1, y1 = main_widget.pattern_widget.sq_items[0].getData()
    x2, y2 = main_widget.pattern_widget.sq_items[1].getData()

    assert x1[-1] != x2[-1]


def test_correct_configuration_selected_after_remove(main_widget, configuration_widget, model):
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)

    configuration_widget.configuration_tw.selectRow(1)
    assert model.configuration_ind == 1

    click_button(configuration_widget.remove_btn)
    assert model.configuration_ind == 1
    assert configuration_widget.configuration_tw.currentRow() == 1


def test_changing_configuration_visibility(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)

    click_checkbox(configuration_widget.configuration_show_cbs[1])

    assert not main_widget.pattern_widget.gr_items[1] in \
               main_widget.pattern_widget.gr_plot.items
    assert not main_widget.pattern_widget.sq_items[1] in \
               main_widget.pattern_widget.sq_plot.items


def test_changing_configuration_color(main_widget, configuration_widget):
    click_button(configuration_widget.freeze_btn)
    click_button(configuration_widget.freeze_btn)

    # changing a non-active configuration will change its color immediately in the pattern widget:
    new_color = QtGui.QColor(233, 1, 3)
    QtWidgets.QColorDialog.getColor = MagicMock(return_value=new_color)
    click_button(configuration_widget.configuration_color_btns[1])
    assert main_widget.pattern_widget.gr_items[1].opts['pen'].color().rgb() == new_color.rgb()
    assert main_widget.pattern_widget.sq_items[1].opts['pen'].color().rgb() == new_color.rgb()

    # changing the active configuration will change its color only after the next freeze:
    new_color = QtGui.QColor(1, 1, 3)
    QtWidgets.QColorDialog.getColor = MagicMock(return_value=new_color)
    click_button(configuration_widget.configuration_color_btns[2])
    assert main_widget.pattern_widget.gr_items[1].opts['pen'].color().rgb() != new_color.rgb()
    assert main_widget.pattern_widget.sq_items[1].opts['pen'].color().rgb() != new_color.rgb()

    click_button(configuration_widget.freeze_btn)
    assert main_widget.pattern_widget.gr_items[2].opts['pen'].color().rgb() == new_color.rgb()
    assert main_widget.pattern_widget.sq_items[2].opts['pen'].color().rgb() == new_color.rgb()

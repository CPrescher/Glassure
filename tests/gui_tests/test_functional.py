# -*- coding: utf-8 -*-
import numpy as np
from .utility import set_widget_text, click_checkbox, click_button, prepare_file_loading
from glassure.gui.widgets.control.options import OptionsWidget
from glassure.gui.widgets.control.composition import CompositionWidget
from glassure.gui.widgets.control.extrapolation import ExtrapolationWidget
from glassure.gui.widgets.control.configuration import ConfigurationWidget
from glassure.gui.widgets.glassure_widget import GlassureWidget
from glassure.gui.widgets.custom.pattern import PatternWidget
from glassure.gui.controller.glassure_controller import GlassureController
from glassure.gui.model.glassure_model import GlassureModel


def test_normal_workflow(main_controller: GlassureController, main_widget: GlassureWidget,
                         pattern_widget: PatternWidget, composition_widget: CompositionWidget,
                         extrapolation_widget: ExtrapolationWidget, model: GlassureModel):
    # Edd opens the program and wants to load his data and background file:

    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()

    # he gives the composition of the sample and the normalization procedure is automatically done and he sees
    # a computed g(r) and s(q)

    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    composition_widget.add_element('Mg', 2)
    composition_widget.add_element('Si', 1)
    composition_widget.add_element('O', 4)

    assert model.composition == {'Mg': 2, 'Si': 1, 'O': 4}

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # Now he wants to enter the correct density value:
    prev_gr_data = pattern_widget.gr_items[0].getData()
    set_widget_text(main_widget.density_txt, 2.9)
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # Then he adjusts the scale of the background data and it automatically adjusts sq and gr
    prev_sq_data = main_widget.pattern_widget.sq_items[0].getData()
    prev_gr_data = main_widget.pattern_widget.gr_items[0].getData()

    main_widget.bkg_scaling_sb.setValue(0.5)

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # now he adjusts the smoothing and sees the things change in respect to
    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    main_widget.smooth_sb.setValue(3)

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # now he wants to see how the data looks when choosing a larger Q-range
    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    set_widget_text(main_widget.q_max_txt, 12)

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # he thinks there are still strong oscillations at the lower r-region, and wants to see what the Loch
    # modification function will do

    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    click_checkbox(main_widget.use_modification_cb, left=False)

    assert np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # this looks nice, but what if we use a different normalization method?

    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    click_checkbox(main_widget.left_control_widget.options_widget.normalization_method_fit, left=False)

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # he does not like the current formalism and changes it to AL
    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    click_checkbox(main_widget.left_control_widget.options_widget.sq_method_AL, left=False)

    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # the data unfortunately is not measured up to a Q of 0 A^-1, however the missing data below 1 A^-1 is already
    # extrapolated with a step function, he thinks the polynomial option might be a better choice, selects it and
    # sees the change:

    click_checkbox(extrapolation_widget.activate_cb)
    assert pattern_widget.sq_items[0].getData()[0][0] < 0.5

    prev_sq_data = pattern_widget.sq_items[0].getData()
    click_checkbox(extrapolation_widget.poly_extrapolation_rb)
    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())

    # changing the q_max value, gives an even better result for the polynomial extrapolation

    prev_sq_data = pattern_widget.sq_items[0].getData()
    set_widget_text(main_widget.extrapolation_q_max_txt, 1.5)
    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())

    # looks good already! However, the oscillations below 1 Angstrom bother him still a lot, so he wants to
    # optimize this by using the Eggert et al. (2002) method:

    prev_sq_data = pattern_widget.sq_items[0].getData()
    click_checkbox(main_widget.optimize_activate_cb)
    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())

    # However he realizes that the default cutoff might too low for this kind of data. and gives a larger number,
    # and optimizes again:

    prev_sq_data = pattern_widget.sq_items[0].getData()
    set_widget_text(main_widget.optimize_r_cutoff_txt, 1.2)
    assert not np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())


def test_working_with_configurations(main_controller: GlassureController, main_widget: GlassureWidget,
                                     composition_widget: CompositionWidget):
    # Edd starts to mak some analysis
    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()

    composition_widget.add_element('Si', 1)

    # He likes the default parameters, but wants to test it against another density, therefore he saves the current
    # state

    click_button(main_widget.freeze_configuration_btn)

    # and magically sees that there are now is a field in the configuration table and extra other lines in the plot
    # widgets

    assert main_widget.configuration_tw.rowCount() == 2


def test_reset_background(main_controller: GlassureController, main_widget: GlassureWidget,
                          pattern_widget: PatternWidget, composition_widget: CompositionWidget,
                          extrapolation_widget: ExtrapolationWidget, model: GlassureModel):
    # Edd opens the program and wants to load his data and background file:
    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()

    # Suddenly he realizes that he loaded the wrong background file, and wants to reset it
    click_button(main_widget.reset_bkg_btn)

    assert model.background_pattern is None
    assert pattern_widget.bkg_item.getData()[0] is None
    assert pattern_widget.bkg_item.getData()[1] is None


def test_using_different_fourier_transform_methods(main_controller: GlassureController, main_widget: GlassureWidget,
                                                   pattern_widget: PatternWidget, composition_widget: CompositionWidget,
                                                   extrapolation_widget: ExtrapolationWidget, model: GlassureModel):
    # Edd opens the program and wants to load his data and background file:
    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()

    # he gives the composition of the sample, and the normalization procedure is automatically done, and he sees
    # a computed g(r) and s(q)

    composition_widget.add_element('Mg', 2)
    composition_widget.add_element('Si', 1)
    composition_widget.add_element('O', 4)

    # he wants to see how the data looks when choosing a different fourier transform method
    prev_sq_data = pattern_widget.sq_items[0].getData()
    prev_gr_data = pattern_widget.gr_items[0].getData()

    assert main_widget.left_control_widget.options_widget.fft_cb.isChecked()
    click_checkbox(main_widget.left_control_widget.options_widget.fft_cb, left=False)
    assert not main_widget.left_control_widget.options_widget.fft_cb.isChecked()

    assert np.array_equal(prev_sq_data, pattern_widget.sq_items[0].getData())
    assert not np.array_equal(prev_gr_data, pattern_widget.gr_items[0].getData())

    # he is satisfied with the small changes and will continue to use the fft method

# -*- coding: utf-8 -*-
import pytest
import numpy as np

from glassure.core import Pattern
from .utility import click_button, click_checkbox,  prepare_file_loading


@pytest.fixture
def setup(main_controller, model):
    model.q_min = 1.5
    model.q_max = 10

    composition_widget = main_controller.main_widget.left_control_widget.composition_widget
    composition_widget.add_element('O', 2)
    composition_widget.add_element('Si', 1)

    prepare_file_loading('glass_rod_SS.xy')
    main_controller.load_data()
    main_controller.load_bkg()
    model.background_scaling = 0


def test_activate_transfer_correction(setup, main_controller, transfer_widget, model):
    click_checkbox(transfer_widget.activate_cb)
    assert model.use_transfer_function


def test_loading_sample_data(setup, main_controller, transfer_widget, model):
    click_button(transfer_widget.load_sample_btn)
    assert model.transfer_sample_pattern is not None
    assert str(transfer_widget.sample_filename_lbl.text()) == 'glass_rod_SS.xy'


def test_loading_sample_bkg_data(setup, main_controller, transfer_widget, model):
    click_button(transfer_widget.load_sample_bkg_btn)
    assert model.transfer_sample_bkg_pattern is not None
    assert str(transfer_widget.sample_bkg_filename_lbl.text()) == 'glass_rod_SS.xy'


def test_loading_std_data(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    assert model.transfer_std_pattern is not None
    assert str(transfer_widget.std_filename_lbl.text()) == 'glass_rod_WOS.xy'


def test_loading_std_bkg_data(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_bkg_btn)
    assert model.transfer_std_bkg_pattern is not None
    assert str(transfer_widget.std_bkg_filename_lbl.text()) == 'glass_rod_WOS.xy'


def test_transfer_function_exists(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)

    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    assert model.transfer_function is None
    click_checkbox(transfer_widget.activate_cb)
    assert model.transfer_function is not None


def test_transfer_function_modifies_pattern(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    _, y_before = model.sq_pattern.data
    click_checkbox(transfer_widget.activate_cb)
    _, y_after = model.sq_pattern.data

    assert not np.array_equal(y_before, y_after)


def test_change_sample_bkg_scaling(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    sample_bkg_pattern = Pattern(model.transfer_sample_pattern.x,
                                 np.ones(model.transfer_sample_pattern.y.shape))

    model.transfer_sample_bkg_pattern = sample_bkg_pattern
    model.transfer_sample_bkg_scaling = 0
    click_checkbox(transfer_widget.activate_cb)

    _, y_before = model.sq_pattern.data
    transfer_widget.sample_bkg_scaling_sb.setValue(50)
    assert model.transfer_sample_bkg_scaling == 50
    _, y_after = model.sq_pattern.data

    assert not np.array_equal(y_after, y_before)


def test_change_std_bkg_scaling(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    std_bkg_pattern = Pattern(model.transfer_std_pattern.x,
                              np.ones(model.transfer_std_pattern.y.shape))

    model.transfer_std_bkg_pattern = std_bkg_pattern
    model.transfer_std_bkg_scaling = 0
    click_checkbox(transfer_widget.activate_cb)

    _, y_before = model.sq_pattern.data
    transfer_widget.std_bkg_scaling_sb.setValue(50)
    assert model.transfer_std_bkg_scaling == 50
    _, y_after = model.sq_pattern.data

    assert not np.array_equal(y_after, y_before)


def test_change_smoothing(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    click_checkbox(transfer_widget.activate_cb)

    _, y_before = model.sq_pattern.data
    transfer_widget.smooth_sb.setValue(10)
    assert model.transfer_function_smoothing == 10
    _, y_after = model.sq_pattern.data

    assert not np.array_equal(y_after, y_before)


def test_transfer_function_gets_deactivated(setup, main_controller, transfer_widget, model):
    prepare_file_loading('glass_rod_WOS.xy')
    click_button(transfer_widget.load_std_btn)
    prepare_file_loading('glass_rod_SS.xy')
    click_button(transfer_widget.load_sample_btn)

    click_checkbox(transfer_widget.activate_cb)

    _, y_before = model.sq_pattern.data
    click_checkbox(transfer_widget.activate_cb)
    _, y_after = model.sq_pattern.data

    assert not np.array_equal(y_after, y_before)

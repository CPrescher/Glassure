# -*- coding: utf-8 -*-
from .utility import click_checkbox, array_almost_equal, prepare_file_loading


def test_activate_soller_correction(main_controller, soller_widget, composition_widget, model):
    # prepare data

    composition_widget.add_element('Mg', 2)
    composition_widget.add_element('Si', 1)
    composition_widget.add_element('O', 4)

    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()

    # test activation
    _, prev_sq = model.sq_pattern.data
    click_checkbox(soller_widget.activate_cb)

    _, new_sq = model.sq_pattern.data

    assert not array_almost_equal(prev_sq, new_sq)

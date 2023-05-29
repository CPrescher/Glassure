# -*- coding: utf-8 -*-
import numpy as np
import pytest

from .utility import click_checkbox, set_widget_text, prepare_file_loading


@pytest.fixture
def setup(main_controller):
    prepare_file_loading('Mg2SiO4_ambient.xy')
    main_controller.load_data()
    prepare_file_loading('Mg2SiO4_ambient_bkg.xy')
    main_controller.load_bkg()
    main_controller.main_widget.left_control_widget.composition_widget.add_element('Si', 1)
    main_controller.main_widget.left_control_widget.composition_widget.add_element('O', 4)
    main_controller.main_widget.left_control_widget.composition_widget.add_element('Mg', 2)


def test_activating_extrapolation(setup, main_controller, extrapolation_widget, model):
    if extrapolation_widget.activate_cb.isChecked():
        click_checkbox(extrapolation_widget.activate_cb)

    # without extrapolation S(Q) should have no values below
    q, sq = model.sq_pattern.data
    assert q[0] > 1

    # when turning extrapolation on, it should automatically interpolate sq of to zero and recalculate everything
    # by default a Step function should be used
    click_checkbox(extrapolation_widget.activate_cb)

    assert extrapolation_widget.activate_cb.isChecked()

    q, sq = model.sq_pattern.limit(0, 1).data
    assert q[0] < 0.1
    assert np.sum(sq) == 0


def test_different_extrapolation_methods(setup, main_controller, extrapolation_widget, model):
    if not extrapolation_widget.activate_cb.isChecked():
        click_checkbox(extrapolation_widget.activate_cb)

    # next we activate the linear Extrapolation method to see how this changes the g(r)
    # using a linear extrapolation to zero the sum between 0 and 0.5 should be always different from 0:
    click_checkbox(extrapolation_widget.linear_extrapolation_rb)
    q, sq = model.sq_pattern.limit(0, 1).data

    assert not np.sum(sq[np.where(q < 0.4)]) == 0

    # now switching on spline extrapolation and see how this effects the pattern
    prev_q, prev_sq = model.sq_pattern.limit(0, 2).data
    click_checkbox(extrapolation_widget.spline_extrapolation_rb)
    after_q, after_sq = model.sq_pattern.limit(0, 2).data

    assert not np.array_equal(prev_sq, after_sq)


def test_polynomial_parameters(setup, main_controller, extrapolation_widget, qtbot):
    model = main_controller.model

    click_checkbox(extrapolation_widget.poly_extrapolation_rb)

    prev_q, prev_sq = model.sq_pattern.limit(0, 2).data
    set_widget_text(extrapolation_widget.q_max_txt, 1.5)
    after_q, after_sq = model.sq_pattern.limit(0, 2).data

    assert not np.array_equal(prev_sq, after_sq)

    # there seems to be a strange connection between the two parts, lets use the replace option and see the change
    prev_q, prev_sq = model.sq_pattern.limit(0, 2).data
    click_checkbox(extrapolation_widget.replace_cb)
    after_q, after_sq = model.sq_pattern.limit(0, 2).data

    assert not np.array_equal(prev_sq, after_sq)

# -*- coding: utf-8 -*-
from qtpy.QtCore import Qt
import numpy as np
from numpy.testing import assert_array_equal

from glassure.gui.widgets.glassure_widget import GlassureWidget
from glassure.gui.model.configuration import GlassureConfiguration
from glassure.core.pattern import Pattern
from .utility import set_widget_text


def test_freeze_configuration(configuration_widget, qtbot):
    assert configuration_widget.configuration_tw.rowCount() == 1

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2
    assert configuration_widget.configuration_tw.columnCount() == 3

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 4


def test_remove_configuration(configuration_widget, qtbot):
    assert configuration_widget.configuration_tw.rowCount() == 1
    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 1

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)

    assert configuration_widget.configuration_tw.rowCount() == 3

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2


def create_alternative_configuration():
    config = GlassureConfiguration()
    config.original_pattern.load("tests/data/Mg2SiO4_ambient.xy")
    config.background_pattern = Pattern.from_file(
        "tests/data/Mg2SiO4_ambient_bkg.xy")
    config.diamond_bkg_pattern = Pattern.from_file(
        "tests/data/Mg2SiO4_ambient.xy")

    config.composition = {'Mg': 2, 'Si': 1, 'O': 4}
    config.q_min = 0.5
    config.q_max = 20
    config.density = 3.51

    config.r_min = 0.01
    config.r_max = 12
    config.r_step = 0.02

    config.optimize = True
    config.optimize_r_cutoff = 1.6
    config.optimize_iterations = 10
    config.optimize_attenuation = 3

    config.use_modification_fcn = True
    config.extrapolation_method = "Herbert"
    config.extrapolation_parameters = {'a': 1, 'b': 2, 'c': 3}

    config.use_soller_correction = True
    config.soller_correction = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    config.soller_parameters = {'a': 3, 'b': 2, 'c': 1}

    config.use_transfer_function = False

    config.transfer_function_smoothing = 1.0
    config.transfer_std_pattern = Pattern.from_file(
        "tests/data/glass_rod_WOS.xy")
    config.transfer_std_bkg_pattern = Pattern.from_file(
        "tests/data/glass_rod_WOS.xy")
    config.transfer_std_bkg_pattern.y -= 10
    config.transfer_std_bkg_scaling = 1.0

    config.transfer_sample_pattern = Pattern.from_file(
        "tests/data/glass_rod_WOS.xy")
    config.transfer_sample_bkg_pattern = Pattern.from_file(
        "tests/data/glass_rod_WOS.xy")
    config.transfer_sample_bkg_pattern.y -= 10
    config.transfer_sample_bkg_scaling = 1
    config.transfer_function = config.transfer_std_pattern.y /\
        config.transfer_sample_pattern.y

    config.name = 'Config {}'.format(GlassureConfiguration.num)
    config.color = np.array([1, 23, 24])
    return config


def compare_config_and_dict(config: GlassureConfiguration, config_dict: dict):
    assert config_dict['original_pattern'] == config.original_pattern.to_dict()
    assert config_dict['background_pattern'] == \
        config.background_pattern.to_dict()
    assert config_dict['diamond_bkg_pattern'] == \
        config.diamond_bkg_pattern.to_dict()
    assert config_dict['composition'] == config.composition
    assert config_dict['q_min'] == config.q_min
    assert config_dict['q_max'] == config.q_max
    assert config_dict['density'] == config.density
    assert config_dict['r_min'] == config.r_min
    assert config_dict['r_max'] == config.r_max
    assert config_dict['r_step'] == config.r_step
    assert config_dict['optimize'] == config.optimize
    assert config_dict['optimize_r_cutoff'] == config.optimize_r_cutoff
    assert config_dict['optimize_iterations'] == config.optimize_iterations
    assert config_dict['optimize_attenuation'] == config.optimize_attenuation
    assert config_dict['use_modification_fcn'] == config.use_modification_fcn
    assert config_dict['extrapolation_method'] == config.extrapolation_method
    assert config_dict['extrapolation_parameters'] == \
        config.extrapolation_parameters
    assert config_dict['use_soller_correction'] == config.use_soller_correction
    assert list(config_dict['soller_correction']) ==  \
        list(config.soller_correction)
    assert config_dict['soller_parameters'] == config.soller_parameters
    assert config_dict['use_transfer_function'] == config.use_transfer_function
    assert config_dict['transfer_function_smoothing'] == \
        config.transfer_function_smoothing
    assert config_dict['transfer_std_pattern'] == \
        config.transfer_std_pattern.to_dict()
    assert config_dict['transfer_std_bkg_pattern'] ==\
        config.transfer_std_bkg_pattern.to_dict()
    assert config_dict['transfer_std_bkg_scaling'] == \
        config.transfer_std_bkg_scaling
    assert config_dict['transfer_sample_pattern'] == \
        config.transfer_sample_pattern.to_dict()
    assert config_dict['transfer_sample_bkg_pattern'] == \
        config.transfer_sample_bkg_pattern.to_dict()
    assert config_dict['transfer_sample_bkg_scaling'] == \
        config.transfer_sample_bkg_scaling
    assert_array_equal(config_dict['transfer_function'],
                       config.transfer_function)
    assert config_dict['name'] == config.name
    assert config_dict['color'] == config.color.tolist()
    assert config_dict['sq_pattern'] is None
    assert config_dict['fr_pattern'] is None
    assert config_dict['gr_pattern'] is None


def test_to_dict():
    config = create_alternative_configuration()
    config_dict = config.to_dict()
    compare_config_and_dict(config, config_dict)


def test_from_dict():
    config = create_alternative_configuration()
    config_dict = config.to_dict()
    config2 = GlassureConfiguration.from_dict(config_dict)
    compare_config_and_dict(config, config2.to_dict())


def test_remove_configuration_changes_to_correct_configuration(
        main_widget: GlassureWidget, configuration_widget, model,
        qtbot):

    assert configuration_widget.configuration_tw.rowCount() == 1
    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    set_widget_text(main_widget.q_max_txt, '13')
    assert model.q_max == 13

    qtbot.mouseClick(configuration_widget.freeze_btn, Qt.LeftButton)
    set_widget_text(main_widget.q_max_txt, '14')
    assert model.q_max == 14

    assert configuration_widget.configuration_tw.rowCount() == 3

    configuration_widget.configuration_tw.setCurrentCell(0, 0)
    assert model.q_max == 10
    assert model.configuration_ind == 0

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 2
    assert model.configuration_ind == 0
    assert model.q_max == 13
    assert main_widget.q_max_txt.text() == '13.0'

    configuration_widget.configuration_tw.setCurrentCell(1, 0)
    assert model.configuration_ind == 1
    assert model.q_max == 14
    assert main_widget.q_max_txt.text() == '14.0'

    qtbot.mouseClick(configuration_widget.remove_btn, Qt.LeftButton)
    assert configuration_widget.configuration_tw.rowCount() == 1
    assert model.configuration_ind == 0
    assert model.q_max == 13
    assert main_widget.q_max_txt.text() == '13.0'

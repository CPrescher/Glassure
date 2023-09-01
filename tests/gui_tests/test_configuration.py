# -*- coding: utf-8 -*-
from qtpy.QtCore import Qt
import numpy as np
from numpy.testing import assert_array_equal

from glassure.gui.widgets.glassure_widget import GlassureWidget
from glassure.gui.model.configuration import GlassureConfiguration, Sample, \
    OptimizeConfiguration, ExtrapolationConfiguration, TransformConfiguration
from glassure.core.pattern import Pattern
from .utility import set_widget_text, data_path


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
    config.original_pattern.load(data_path("Mg2SiO4_ambient.xy"))
    config.background_pattern = Pattern.from_file(data_path("Mg2SiO4_ambient_bkg.xy"))
    config.diamond_bkg_pattern = Pattern.from_file(data_path("Mg2SiO4_ambient.xy"))

    config.sample.density = 3.51
    config.sample.composition = {'Mg': 2, 'Si': 1, 'O': 4}

    config.transform_config.q_min = 0.5
    config.transform_config.q_max = 20
    config.transform_config.r_min = 0.01
    config.transform_config.r_max = 12
    config.transform_config.r_step = 0.02
    config.transform_config.use_modification_fcn = True

    config.optimize_config.enable = True
    config.optimize_config.r_cutoff = 1.6
    config.optimize_config.iterations = 10
    config.optimize_config.attenuation = 3

    config.extrapolation_config.method = "Herbert"
    config.extrapolation_config.s0 = 0.3
    config.extrapolation_config.s0_auto = False
    config.extrapolation_config.fit_q_max = 2.1
    config.extrapolation_config.fit_replace = True

    config.soller_config.enable = True
    config.soller_config.correction = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    config.soller_config.parameters = {'a': 3, 'b': 2, 'c': 1}

    config.transfer_config.enable = False
    config.transfer_config.function_smoothing = 1.0
    config.transfer_config.std_pattern = Pattern.from_file(data_path("glass_rod_WOS.xy"))
    config.transfer_config.std_bkg_pattern = Pattern.from_file(data_path("glass_rod_WOS.xy"))
    config.transfer_config.std_bkg_pattern.y -= 10
    config.transfer_config.std_bkg_scaling = 1.0

    config.transfer_config.sample_pattern = Pattern.from_file(data_path("glass_rod_WOS.xy"))
    config.transfer_config.sample_bkg_pattern = Pattern.from_file(data_path("glass_rod_WOS.xy"))
    config.transfer_config.sample_bkg_pattern.y -= 10
    config.transfer_config.sample_bkg_scaling = 1

    config.name = 'Config {}'.format(GlassureConfiguration.num)
    config.color = np.array([1, 23, 24])
    return config


def compare_config_and_dict(config: GlassureConfiguration, config_dict: dict):
    assert config_dict['original_pattern'] == config.original_pattern.to_dict()
    assert config_dict['background_pattern'] == config.background_pattern.to_dict()
    assert config_dict['diamond_bkg_pattern'] == config.diamond_bkg_pattern.to_dict()

    assert config_dict['sq_pattern'] is None
    assert config_dict['fr_pattern'] is None
    assert config_dict['gr_pattern'] is None

    assert config_dict['sample']['composition'] == config.sample.composition
    assert config_dict['sample']['density'] == config.sample.density

    assert config_dict['transform_configuration']['q_min'] == config.transform_config.q_min
    assert config_dict['transform_configuration']['q_max'] == config.transform_config.q_max
    assert config_dict['transform_configuration']['r_min'] == config.transform_config.r_min
    assert config_dict['transform_configuration']['r_max'] == config.transform_config.r_max
    assert config_dict['transform_configuration']['r_step'] == config.transform_config.r_step
    assert config_dict['transform_configuration']['use_modification_fcn'] == \
           config.transform_config.use_modification_fcn

    assert config_dict['extrapolation_configuration'] == config.extrapolation_config.to_dict()

    assert config_dict['optimize_configuration']['enable'] == config.optimize_config.enable
    assert config_dict['optimize_configuration']['r_cutoff'] == config.optimize_config.r_cutoff
    assert config_dict['optimize_configuration']['iterations'] == config.optimize_config.iterations
    assert config_dict['optimize_configuration']['attenuation'] == config.optimize_config.attenuation

    assert config_dict['soller_configuration']['enable'] == config.soller_config.enable
    assert list(config_dict['soller_configuration']['correction']) == list(config.soller_config.correction)
    assert config_dict['soller_configuration']['parameters'] == config.soller_config.parameters

    assert config_dict['transfer_configuration']['enable'] == config.transfer_config.enable
    assert config_dict['transfer_configuration']['smoothing'] == config.transfer_config.function_smoothing
    assert config_dict['transfer_configuration']['std_pattern'] == config.transfer_config.std_pattern.to_dict()
    assert config_dict['transfer_configuration']['std_bkg_pattern'] == config.transfer_config.std_bkg_pattern.to_dict()
    assert config_dict['transfer_configuration']['std_bkg_scaling'] == config.transfer_config.std_bkg_scaling
    assert config_dict['transfer_configuration']['sample_pattern'] == config.transfer_config.sample_pattern.to_dict()
    assert config_dict['transfer_configuration'][
               'sample_bkg_pattern'] == config.transfer_config.sample_bkg_pattern.to_dict()
    assert config_dict['transfer_configuration']['sample_bkg_scaling'] == config.transfer_config.sample_bkg_scaling

    assert config_dict['name'] == config.name
    assert config_dict['color'] == config.color.tolist()


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


def test_convert_transform_configuration_to_and_from_dict():
    transform_config1 = TransformConfiguration()
    transform_dict1 = transform_config1.to_dict()
    transform_dict1['q_min'] = 0.0
    transform_dict1['q_max'] = 10
    transform_dict1['r_min'] = 0.5
    transform_dict1['sq_method'] = 'FZ'
    transform_config2 = TransformConfiguration.from_dict(transform_dict1)
    transform_dict2 = transform_config2.to_dict()
    assert transform_dict1 == transform_dict2

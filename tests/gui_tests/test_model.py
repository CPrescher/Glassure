# -*- coding: utf-8 -*-
import numpy as np
import pytest

from glassure.gui.model.configuration import SqMethod, NormalizationMethod, ExtrapolationConfiguration, Sample, \
    TransformConfiguration
from .test_configuration import create_alternative_configuration, compare_config_and_dict

from glassure.core import Pattern
from glassure.core import calculate_sq
from glassure.gui.model.glassure_model import GlassureModel
from .utility import data_path


# We use a clean model fixture for the tests, the conftest fixtures is derived
# from the main controller and also includes feedback with the GUI, which is
# not needed here.
@pytest.fixture
def model():
    return GlassureModel()


@pytest.fixture
def setup(model: GlassureModel):
    model.load_data(data_path('Mg2SiO4_ambient.xy'))
    model.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))


def test_set_background_scaling(setup, model: GlassureModel):
    scaling = 0.83133015
    model.background_scaling = scaling
    assert model.background_scaling == scaling
    assert model.background_pattern.scaling == scaling

    original_bkg_pattern = Pattern.from_file(
        data_path('Mg2SiO4_ambient_bkg.xy'))
    x, y = (scaling * original_bkg_pattern).data
    assert np.sum(np.abs(model.background_pattern.data[1] - y)) == 0


def test_calculate_transforms(setup, model: GlassureModel):
    data_pattern = Pattern.from_file(data_path('Mg2SiO4_ambient.xy'))
    bkg_pattern = Pattern.from_file(data_path('Mg2SiO4_ambient_bkg.xy'))

    odata1_x, odata1_y = model.original_pattern.data
    odata2_x, odata2_y = data_pattern.data
    assert np.sum(np.abs(odata1_y - odata2_y)) == 0

    bkg_data1_x, bkg_data1_y = model.background_pattern.data
    bkg_data2_x, bkg_data2_y = bkg_pattern.data
    assert np.sum(np.abs(bkg_data2_y - bkg_data1_y)) == 0

    transform_config = TransformConfiguration()
    data_pattern = data_pattern.limit(0, transform_config.q_max)
    bkg_pattern = bkg_pattern.limit(0, transform_config.q_max)
    background_scaling = 0.83133015

    sample_config = Sample()
    sample_config.sf_source = 'hajdu'
    sample_config.density = 1.7
    sample_config.composition = {
        'Mg': 2,
        'Si': 1,
        'O': 4,
    }

    model.background_scaling = background_scaling
    model.update_parameter(sample_config,
                           transform_config,
                           ExtrapolationConfiguration(), False, 1.5, 5, 1)

    sq_pattern1_x, sq_pattern1_y = model.sq_pattern.data

    sample_pattern = data_pattern - background_scaling * bkg_pattern
    sq_pattern_core = calculate_sq(sample_pattern, sample_config.density, sample_config.composition)
    sq_pattern2_x, sq_pattern2_y = sq_pattern_core.data

    assert len(sq_pattern1_x) == len(sq_pattern2_x)
    assert np.mean(np.abs(sq_pattern1_y - sq_pattern2_y)) == 0


def test_calculate_transforms_without_bkg(model):
    model.load_data(data_path('Mg2SiO4_ambient.xy'))
    sample_config = Sample()
    sample_config.sf_source = 'hajdu'
    sample_config.density = 1.7
    sample_config.composition = {'Mg': 2, 'Si': 1, 'O': 4}

    model.update_parameter(sample_config,
                           TransformConfiguration(),
                           ExtrapolationConfiguration(), False, 1.5, 5, 1)

    assert model.sq_pattern is not None
    assert model.gr_pattern is not None
    assert model.fr_pattern is not None


def test_changing_fourier_transform_method(setup, model: GlassureModel):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    model.transform_config.fourier_transform_method = 'fft'
    model.calculate_transforms()
    fr1 = model.fr_pattern

    model.transform_config.fourier_transform_method = 'integral'
    model.calculate_transforms()
    fr2 = model.fr_pattern
    assert not np.allclose(fr1.y, fr2.y)


def test_calculate_spectra(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    assert model.sq_pattern is not None
    assert model.gr_pattern is not None
    assert model.fr_pattern is not None


def test_changing_comp(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
    sq1 = model.sq_pattern
    model.composition = {'Mg': 1, 'Si': 1.0, 'O': 3.0}
    sq2 = model.sq_pattern
    assert not np.allclose(sq1.y, sq2.y)


def test_changing_q_range(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
    model.extrapolation_config.method = None
    model.calculate_transforms()
    sq = model.sq_pattern
    assert np.min(sq.x) > model.q_min
    assert np.max(sq.x) < model.q_max

    model.q_min = 1.4
    sq = model.sq_pattern
    assert np.min(sq.x) > model.q_min

    model.q_max = 9
    sq = model.sq_pattern
    assert np.max(sq.x) < model.q_max


def test_changing_density(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
    sq1 = model.sq_pattern
    model.density = 2.9
    sq2 = model.sq_pattern
    assert not np.allclose(sq1.y, sq2.y)


def test_changing_r_range(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
    fr = model.fr_pattern
    assert np.min(fr.x) == pytest.approx(model.r_min)
    assert np.max(fr.x) == pytest.approx(model.r_max)

    model.r_min = 1.4
    fr = model.fr_pattern
    assert np.min(fr.x) == pytest.approx(model.r_min)

    model.r_max = 9
    fr = model.fr_pattern
    assert np.max(fr.x) == pytest.approx(model.r_max)


def test_use_modification_fcn(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    fr1 = model.fr_pattern
    model.use_modification_fcn = True
    fr2 = model.fr_pattern
    assert not np.allclose(fr1.y, fr2.y)


def test_changing_sq_method(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    sq1 = model.sq_pattern
    model.sq_method = SqMethod.AL
    sq2 = model.sq_pattern
    assert not np.allclose(sq1.y, sq2.y)


def test_changing_normalization_method(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    sq1 = model.sq_pattern
    model.normalization_method = NormalizationMethod.FIT
    sq2 = model.sq_pattern
    assert not np.allclose(sq1.y, sq2.y)


def test_optimize_sq(setup, model):
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}

    sq1 = model.sq_pattern
    model.optimize = True
    sq2 = model.sq_pattern
    assert not np.allclose(sq1.y, sq2.y)


def test_adding_a_configuration(setup, model):
    # Adding a configuration and then change one parameter to see if new configuration behaves independently
    model.composition = {'Mg': 2.0, 'Si': 1.0, 'O': 4.0}
    sq1 = model.sq_pattern

    assert np.max(sq1.x) < 10

    model.add_configuration()
    sq2 = model.sq_pattern

    assert np.max(sq2.x) < 10

    model.q_max = 12
    sq2 = model.sq_pattern

    assert np.max(sq2.x) < 12


def test_select_configuration(setup, model):
    model.add_configuration()
    model.q_max = 12

    model.add_configuration()
    model.q_max = 14

    model.select_configuration(0)
    assert model.q_max, 10

    model.select_configuration(1)
    assert model.q_max, 12

    model.select_configuration(2)
    assert model.q_max, 14


def test_remove_configuration_with_only_one_left(setup, model):
    # should not remove the last configuration!
    model.remove_configuration()
    assert len(model.configurations) == 1


def test_remove_last_configuration(setup, model):
    model.add_configuration()
    model.q_max = 12
    model.add_configuration()
    model.q_max = 14

    assert model.q_max == 14
    model.remove_configuration()
    assert model.q_max == 12

    model.select_configuration(1)
    model.remove_configuration()
    assert model.q_max == 10


def test_remove_center_configuration(setup, model):
    model.add_configuration()
    model.q_max = 12
    model.add_configuration()
    model.q_max = 14

    model.select_configuration(1)
    assert model.q_max == 12
    model.remove_configuration()
    assert model.q_max == 14


def test_use_transfer_function(setup, model):
    sample_path = data_path('glass_rod_SS.xy')
    std_path = data_path('glass_rod_WOS.xy')

    model.load_data(sample_path)
    model.load_bkg(sample_path)
    model.background_scaling = 0
    model.q_min = 0
    model.q_max = 14
    model.composition = {'Si': 1.0, 'O': 2.0}

    sq_pattern_before = model.sq_pattern

    model.load_transfer_sample_pattern(sample_path)
    model.load_transfer_std_pattern(std_path)

    model.use_transfer_function = True
    test_y = model.original_pattern.limit(0, 14).y * model.transfer_function(model.original_pattern.limit(0, 14).x)
    assert np.std(model.transfer_std_pattern.limit(0, 14).y / test_y) == pytest.approx(0, abs=0.2)

    sq_pattern_with_transfer = model.sq_pattern

    assert not np.array_equal(sq_pattern_before.y, sq_pattern_with_transfer.y)


def test_to_dict_from_dict_single(setup, model, tmpdir):
    model.configurations[0] = create_alternative_configuration()
    model.to_json(tmpdir.join('test.json').strpath)
    model2 = GlassureModel()
    model2.read_json(tmpdir.join('test.json').strpath)
    compare_config_and_dict(
        model.configurations[0],
        model2.configurations[0].to_dict()
    )


def test_to_json_from_json_multiple(setup, model: GlassureModel, tmpdir):
    model.configurations[0] = create_alternative_configuration()
    model.configurations[0].name = 'Config 1'
    model.add_configuration()
    model.configurations[1].name = 'laliea'
    model.add_configuration()
    model.configurations[2].name = 'lalalala'
    model.add_configuration()
    model.configurations[3].name = 'lalalalalalala'
    model.to_json(tmpdir.join('test.json').strpath)

    model2 = GlassureModel()
    model2.read_json(tmpdir.join('test.json').strpath)

    assert model2.configurations[0].name == 'Config 1'
    assert model2.configurations[1].name == 'laliea'
    assert model2.configurations[2].name == 'lalalala'
    assert model2.configurations[3].name == 'lalalalalalala'

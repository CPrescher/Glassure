# -*- coding: utf-8 -*-
import numpy as np
import pytest

from glassure.gui.model.new_model import GlassureModel
from glassure.core.methods import FourierTransformMethod, ExtrapolationMethod
from glassure.core.configuration import (
    SampleConfig,
    TransformConfig,
    FitNormalization,
    IntNormalization,
    ExtrapolationConfig,
    OptimizeConfig,
)


from .utility import data_path


# We use a clean model fixture for the tests, the conftest fixtures is derived
# from the main controller and also includes feedback with the GUI, which is
# not needed here.
@pytest.fixture
def model():
    return GlassureModel()


@pytest.fixture
def setup(model: GlassureModel):
    model.load_data(data_path("Mg2SiO4_ambient.xy"))
    model.load_bkg(data_path("Mg2SiO4_ambient_bkg.xy"))
    sample_config = SampleConfig(
        composition={"Mg": 2.0, "Si": 1.0, "O": 4.0},
        density=2.5,
    )
    model.update_sample(sample_config)


def test_load_data(model: GlassureModel):
    model.load_data(data_path("Mg2SiO4_ambient.xy"))
    assert model.input.data is not None
    assert model.input.data.name == "Mg2SiO4_ambient"


def test_load_bkg(model: GlassureModel):
    model.load_bkg(data_path("Mg2SiO4_ambient_bkg.xy"))
    assert model.input.bkg is not None
    assert model.input.bkg.name == "Mg2SiO4_ambient_bkg"


def test_set_bkg_scaling(setup, model: GlassureModel):
    scaling = 0.83133015
    model.bkg_scaling = scaling
    assert model.input.bkg_scaling == scaling
    assert model.bkg_scaling == scaling


def test_calculate_transforms(setup, model: GlassureModel):
    assert model.result.sq is not None
    assert model.result.gr is not None
    assert model.result.fr is not None


def test_calculate_transforms_without_bkg(model):
    model.load_data(data_path("Mg2SiO4_ambient.xy"))
    sample_config = SampleConfig(
        composition={"Mg": 2.0, "Si": 1.0, "O": 4.0},
        density=2.5,
    )
    assert model.result.sq is None
    model.update_sample(sample_config)

    assert model.result.sq is not None
    assert model.result.gr is not None
    assert model.result.fr is not None


def test_changing_transform_config(setup, model: GlassureModel):
    gr1 = model.result.gr

    transform_config = TransformConfig(q_max=12.0)
    model.update_transform(transform_config)
    gr2 = model.result.gr

    assert not np.allclose(gr1.y, gr2.y)


def test_changing_fit_normalization(setup, model: GlassureModel):
    sq1 = model.result.sq

    normalization = FitNormalization(q_cutoff=4.0)
    model.update_normalization(normalization)
    sq2 = model.result.sq

    assert not np.allclose(sq1.y, sq2.y)


def test_change_to_int_normalization(setup, model: GlassureModel):
    sq1 = model.result.sq

    normalization = IntNormalization()
    model.update_normalization(normalization)
    sq2 = model.result.sq

    assert not np.allclose(sq1.y, sq2.y)


def test_change_extrapolation_method(setup, model: GlassureModel):
    sq1 = model.result.sq

    extrapolation = ExtrapolationConfig(method=ExtrapolationMethod.LINEAR)
    model.update_extrapolation(extrapolation)
    sq2 = model.result.sq

    assert not np.array_equal(sq1.y, sq2.y)


def test_optimize_sq(setup, model):
    sq1 = model.result.sq

    optimize = OptimizeConfig(r_cutoff=1.4, iterations=5, use_modification_fcn=False)
    model.update_optimize(optimize)
    sq2 = model.result.sq

    assert not np.array_equal(sq1.y, sq2.y)


def test_adding_a_configuration(setup, model):
    # Adding a configuration and then change one parameter to see
    # if new configuration behaves independently
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
    sample_path = data_path("glass_rod_SS.xy")
    std_path = data_path("glass_rod_WOS.xy")

    model.load_data(sample_path)
    model.load_bkg(sample_path)
    model.bkg_scaling = 0
    model.q_min = 0
    model.q_max = 14
    model.composition = {"Si": 1.0, "O": 2.0}

    sq_pattern_before = model.sq_pattern

    model.load_transfer_sample_pattern(sample_path)
    model.load_transfer_std_pattern(std_path)

    model.use_transfer_function = True
    test_y = model.original_pattern.limit(0, 14).y * model.transfer_function(
        model.original_pattern.limit(0, 14).x
    )
    assert np.std(model.transfer_std_pattern.limit(0, 14).y / test_y) == pytest.approx(
        0, abs=0.2
    )

    sq_pattern_with_transfer = model.sq_pattern

    assert not np.array_equal(sq_pattern_before.y, sq_pattern_with_transfer.y)


def test_to_dict_from_dict_single(setup, model, tmpdir):
    model.configurations[0] = create_alternative_configuration()
    model.to_json(tmpdir.join("test.json").strpath)
    model2 = GlassureModel()
    model2.read_json(tmpdir.join("test.json").strpath)
    compare_config_and_dict(model.configurations[0], model2.configurations[0].to_dict())


def test_to_json_from_json_multiple(setup, model: GlassureModel, tmpdir):
    model.configurations[0] = create_alternative_configuration()
    model.configurations[0].name = "Config 1"
    model.add_configuration()
    model.configurations[1].name = "laliea"
    model.add_configuration()
    model.configurations[2].name = "lalalala"
    model.add_configuration()
    model.configurations[3].name = "lalalalalalala"
    model.to_json(tmpdir.join("test.json").strpath)

    model2 = GlassureModel()
    model2.read_json(tmpdir.join("test.json").strpath)

    assert model2.configurations[0].name == "Config 1"
    assert model2.configurations[1].name == "laliea"
    assert model2.configurations[2].name == "lalalala"
    assert model2.configurations[3].name == "lalalalalalala"

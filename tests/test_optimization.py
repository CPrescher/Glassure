# -*- coding: utf-8 -*-

import os
import pytest
import numpy as np

from glassure import Pattern, convert_density_to_atoms_per_cubic_angstrom
from glassure.utility import (
    extrapolate_to_zero_poly,
    extrapolate_to_zero_linear,
    calculate_f_mean_squared,
    calculate_f_squared_mean,
    calculate_incoherent_scattering,
    calculate_s0,
)
from glassure.transform import calculate_sq, calculate_fr
from glassure.normalization import normalize_fit, normalize
from glassure.configuration import OptimizeConfig
from glassure.optimization import optimize_sq, optimize_density
from glassure.calc import calculate_pdf, create_calculate_pdf_configs
from glassure.methods import ExtrapolationMethod

from . import unittest_data_path

data_path_alloy = os.path.join(unittest_data_path, "Fe81S19.chi")
background_path_alloy = os.path.join(unittest_data_path, "Fe81S19_bkg.chi")

data_path_glass = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
background_path_glass = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")

data_path_SiO2 = os.path.join(unittest_data_path, "SiO2.xy")
background_path_SiO2 = os.path.join(unittest_data_path, "SiO2_bkg.xy")


@pytest.fixture
def data_path():
    """Path to the test data file."""
    return os.path.join(unittest_data_path, "SiO2.xy")


@pytest.fixture
def bkg_path():
    """Path to the background data file."""
    return os.path.join(unittest_data_path, "SiO2_bkg.xy")


@pytest.fixture
def sample(data_path, bkg_path):
    """Create a sample pattern by subtracting background from data."""
    data = Pattern.from_file(data_path)
    bkg = Pattern.from_file(bkg_path)
    sample = data - bkg
    return sample.limit(1, 17)


@pytest.fixture
def sq(normalized_pattern, f_squared_mean, f_mean_squared, composition):
    """Create a sq pattern for testing."""
    sq = calculate_sq(normalized_pattern, f_squared_mean, f_mean_squared)
    sq = extrapolate_to_zero_linear(sq, y0=calculate_s0(composition))
    sq = sq.rebin(0.05)
    sq.x[0] = 1e-10
    return sq


@pytest.fixture
def composition():
    """Sample composition for testing."""
    return {"Si": 1, "O": 2}


@pytest.fixture
def density():
    """Sample density for testing."""
    return 2.2


@pytest.fixture
def atomic_density(composition, density):
    """Calculate atomic density from composition and density."""
    return convert_density_to_atoms_per_cubic_angstrom(composition, density)


@pytest.fixture
def f_squared_mean(composition, sample):
    """Calculate f squared mean for the sample."""
    return calculate_f_squared_mean(composition, sample.x)


@pytest.fixture
def f_mean_squared(composition, sample):
    """Calculate f mean squared for the sample."""
    return calculate_f_mean_squared(composition, sample.x)


@pytest.fixture
def incoherent_scattering(composition, sample):
    """Calculate incoherent scattering for the sample."""
    return calculate_incoherent_scattering(composition, sample.x)


@pytest.fixture
def normalized_pattern(sample, f_squared_mean, incoherent_scattering):
    """Create normalized pattern for testing."""
    _, normalized = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=10
    )
    return normalized


def test_optimize_sq(sq, atomic_density):
    sq_optimized = optimize_sq(sq, 1.4, 5, atomic_density)
    assert not np.allclose(sq.y, sq_optimized.y)


def test_optimize_sq_fft(sq, atomic_density):
    iterations = 5
    r_step = 0.001 # need high value to be accurate for fft
    sq_optimized = optimize_sq(
        sq, 1.3, iterations, atomic_density, fourier_transform_method="integral", r_step=r_step
    )
    fr_optimized = calculate_fr(sq_optimized, method="fft")


    sq_optimized_fft = optimize_sq(
        sq, 1.3, iterations, atomic_density, fourier_transform_method="fft", r_step=r_step
    )
    fr_optimized_fft = calculate_fr(sq_optimized_fft, method="fft")

    assert np.allclose(sq_optimized.y, sq_optimized_fft.y, atol=0.035)
    assert np.allclose(fr_optimized.y, fr_optimized_fft.y, atol=0.1)


def test_optimize_density():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density, density_error = optimize_density(data_config, calculation_config)

    assert density > 0
    assert density != 3.21
    assert density_error > 0


def test_optimize_density_x_range():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.2)

    density_1, density_error_1 = optimize_density(
        data_config, calculation_config, min_range=(0.3, 1.4)
    )

    density_2, density_error_2 = optimize_density(
        data_config, calculation_config, min_range=(0.3, 0.7)
    )

    assert density_1 != density_2


def test_optimize_density_type():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density_gr, density_gr_error = optimize_density(
        data_config,
        calculation_config,
        type="gr",
        min_range=(0.3, 1.0),
        method="lsq",
    )

    density_sq, density_sq_error = optimize_density(
        data_config,
        calculation_config,
        type="sq",
        method="lsq",
    )

    assert density_gr != density_sq
    assert density_gr_error != density_sq_error


def test_optimize_density_method():
    data = Pattern.from_file(data_path_glass)
    background = Pattern.from_file(background_path_glass)
    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 3.21

    data_config, calculation_config = create_calculate_pdf_configs(
        data, composition, density, background
    )

    calculation_config.transform.q_min = 1
    calculation_config.transform.q_max = 16
    calculation_config.transform.extrapolation.method = ExtrapolationMethod.LINEAR
    calculation_config.optimize = OptimizeConfig(r_cutoff=1.4)

    density_gr, density_gr_residual = optimize_density(
        data_config, calculation_config, type="sq", method="nelder"
    )

    density_sq, density_sq_residual = optimize_density(
        data_config, calculation_config, type="sq", method="lsq"
    )

    assert density_gr_residual != density_sq_residual
    assert density_gr != density_sq

    # compare speed of nelder and least_squares
    import time

    start_time = time.time()
    density_gr, density_gr_residual = optimize_density(
        data_config, calculation_config, type="sq", method="nelder"
    )
    nelder_time = time.time() - start_time

    start_time = time.time()
    density_sq, density_sq_residual = optimize_density(
        data_config, calculation_config, type="sq", method="lsq"
    )
    least_squares_time = time.time() - start_time

    print(f"Nelder time: {nelder_time}, Least squares time: {least_squares_time}")
    assert nelder_time > least_squares_time
    print(f"Density: {density_gr}, {density_sq}")

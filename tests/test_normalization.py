import os
import numpy as np
import pytest

from glassure import Pattern
from glassure.utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    convert_density_to_atoms_per_cubic_angstrom,
)
from glassure.normalization import normalize, normalize_fit
from glassure.scattering_factors import calculate_coherent_scattering_factor

from . import unittest_data_path


@pytest.fixture
def data_path():
    return os.path.join(unittest_data_path, "SiO2.xy")


@pytest.fixture
def bkg_path():
    return os.path.join(unittest_data_path, "SiO2_bkg.xy")


@pytest.fixture
def sample(data_path, bkg_path):
    """Create a sample pattern by subtracting background from data."""
    data = Pattern.from_file(data_path)
    bkg = Pattern.from_file(bkg_path)
    sample = data - bkg
    return sample.limit(1, 17)


@pytest.fixture
def composition():
    """Sample composition for testing."""
    return {"Si": 1, "O": 2}


@pytest.fixture
def density():
    """Sample density for testing."""
    return 2.9


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


def test_normalize(
    sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
):
    """Test the normalize function."""
    n, _ = normalize(
        sample,
        atomic_density,
        f_squared_mean,
        f_mean_squared,
        incoherent_scattering,
    )
    assert n > 0


def test_normalize_fit(sample, f_squared_mean, incoherent_scattering):
    """Test the normalize_fit function with different parameters."""
    # Test without multiple scattering
    params_1, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, multiple_scattering=False
    )

    # Test with multiple scattering
    params_2, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, multiple_scattering=True
    )

    # Test with container scattering
    diamond_scattering = calculate_coherent_scattering_factor("C", sample.x)
    params_3, _ = normalize_fit(
        sample,
        f_squared_mean,
        incoherent_scattering,
        container_scattering=diamond_scattering,
    )

    # Verify different parameters produce different results
    assert params_1["n"].value != params_2["n"].value
    assert params_1["n"].value != params_3["n"].value
    assert params_2["multiple"].value > 0
    assert params_3["n_container"].value > 0

    # Test with q_cutoff
    params_4, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    assert params_4["n"].value != params_1["n"].value


def test_normalize_fit_without_incoherent_scattering(sample, f_squared_mean):
    """Test normalize_fit without incoherent scattering."""
    params, _ = normalize_fit(sample, f_squared_mean, None)
    assert params["n"].value > 0


def test_normalize_fit_without_container_scattering_and_with_container_scattering(
    sample, f_squared_mean
):
    """Test normalize_fit with and without container scattering."""
    diamond_scattering = calculate_coherent_scattering_factor("C", sample.x)
    params, _ = normalize_fit(
        sample,
        f_squared_mean,
        None,
        container_scattering=diamond_scattering,
    )
    assert params["n"].value > 0


def test_compare_normalize_and_normalize_fit(
    sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
):
    """Compare results from normalize and normalize_fit functions."""
    n_normalize, normalized_pattern_1 = normalize(
        sample,
        atomic_density,
        f_squared_mean,
        f_mean_squared,
        incoherent_scattering,
    )
    p_normalize_fit, normalized_pattern_2 = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    assert np.isclose(n_normalize, p_normalize_fit["n"].value, rtol=1e-2)

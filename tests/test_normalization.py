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
from glassure.normalization import normalize, normalize_fit, normalize_fit_lmfit
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
    assert isinstance(data, Pattern)
    assert isinstance(bkg, Pattern)

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


def test_normalize_fit(sample, f_squared_mean, incoherent_scattering, f_mean_squared):
    """Test the normalize_fit function with different parameters."""
    # Test without multiple scattering
    params_1, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, multiple_scattering=False
    )

    # Test with multiple scattering
    new_sample = Pattern(sample.x, sample.y + 1e11)
    params_2, _ = normalize_fit(
        new_sample,
        f_squared_mean,
        incoherent_scattering,
        multiple_scattering=True,
    )
    assert params_1["n"] != params_2["n"]
    assert params_2["multiple"] > 1000

    # Test with container scattering
    diamond_scattering = calculate_incoherent_scattering({"C": 1}, sample.x)
    new_sample = Pattern(sample.x, sample.y + 1e11 * diamond_scattering)
    params_3, _ = normalize_fit(
        new_sample,
        f_squared_mean,
        incoherent_scattering,
        container_scattering=diamond_scattering,
        q_cutoff=10,
    )
    # Verify different parameters produce different results
    assert params_1["n"] != params_3["n"]
    assert params_3["n_container"] > 1000

    # Test with q_cutoff
    params_4, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    assert params_4["n"] != params_1["n"]


def test_normalize_fit_without_incoherent_scattering(sample, f_squared_mean):
    """Test normalize_fit without incoherent scattering."""
    params, _ = normalize_fit(sample, f_squared_mean, None)
    assert params["n"] > 0


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
    assert params["n"] > 0


def test_compare_normalize_and_normalize_fit(
    sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
):
    """Compare results from normalize and normalize_fit functions."""
    n_normalize, _ = normalize(
        sample,
        atomic_density,
        f_squared_mean,
        f_mean_squared,
        incoherent_scattering,
    )
    p_normalize_fit, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    assert np.isclose(n_normalize, p_normalize_fit["n"], rtol=1e-2)


# Tests for normalize_fit_lmfit (deprecated) and comparison with normalize_fit (new implementation)
#
# Both implementations should produce identical results (within floating-point precision)
# since they solve the same least squares problem.


def test_normalize_fit_lmfit_basic(sample, f_squared_mean, incoherent_scattering):
    """Test that normalize_fit_lmfit runs and produces reasonable results."""
    params, pattern = normalize_fit_lmfit(
        sample,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=5,
        method="squared",
    )
    assert params["n"].value > 0
    assert len(pattern.y) == len(sample.y)


def test_normalize_fit_lmfit_linear_method(sample, f_squared_mean, incoherent_scattering):
    """Test normalize_fit_lmfit with linear scaling method."""
    params_squared, _ = normalize_fit_lmfit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5, method="squared"
    )
    params_linear, _ = normalize_fit_lmfit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5, method="linear"
    )
    # Different methods should give different results
    assert params_squared["n"].value != params_linear["n"].value


def test_normalize_fit_lmfit_with_multiple_scattering(
    sample, f_squared_mean, incoherent_scattering
):
    """Test normalize_fit_lmfit with multiple scattering enabled."""
    # Add artificial offset to simulate multiple scattering contribution
    # Sample intensity is ~1e9, so add 1e11 to create significant offset
    sample_with_offset = Pattern(sample.x, sample.y + 1e11)

    params, _ = normalize_fit_lmfit(
        sample_with_offset,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=5,
        multiple_scattering=True,
    )
    # Should detect significant multiple scattering (scaled by n)
    assert params["multiple"].value > 1000
    assert params["n"].value > 0


def test_normalize_fit_lmfit_with_container_scattering(
    sample, f_squared_mean, incoherent_scattering
):
    """Test normalize_fit_lmfit with container scattering."""
    diamond_scattering = calculate_incoherent_scattering({"C": 1}, sample.x)
    sample_with_container = Pattern(sample.x, sample.y + 1e11 * diamond_scattering)

    params, pattern = normalize_fit_lmfit(
        sample_with_container,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=8,
        container_scattering=diamond_scattering,
    )
    # Should detect container scattering
    assert params["n_container"].value > 1000
    assert params["n"].value > 0


def test_normalize_fit_lmfit_without_incoherent(sample, f_squared_mean):
    """Test normalize_fit_lmfit without incoherent scattering."""
    params, pattern = normalize_fit_lmfit(
        sample, f_squared_mean, incoherent_scattering=None, q_cutoff=5
    )
    assert params["n"].value > 0


def test_normalize_fit_lmfit_invalid_method(sample, f_squared_mean):
    """Test that normalize_fit_lmfit raises error for invalid method."""
    with pytest.raises(NotImplementedError, match="not an allowed method"):
        normalize_fit_lmfit(sample, f_squared_mean, method="invalid")


def test_normalize_fit_invalid_method(sample, f_squared_mean):
    """Test that normalize_fit raises error for invalid method."""
    with pytest.raises(NotImplementedError, match="not a valid method"):
        normalize_fit(sample, f_squared_mean, method="invalid")


# Comparison tests between old and new implementations
# These document the expected differences due to the bug in normalize_fit_lmfit


def test_compare_normalize_fit_implementations_simple(
    sample, f_squared_mean, incoherent_scattering
):
    """
    Compare normalize_fit_lmfit and normalize_fit for simple case.

    Both implementations solve the same least squares problem and should
    produce identical results within floating-point precision.
    """
    params_lmfit, pattern_lmfit = normalize_fit_lmfit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    params_new, pattern_new = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )

    # Results should be essentially identical
    assert np.isclose(params_lmfit["n"].value, params_new["n"], rtol=1e-6, atol=0), (
        f"Normalization factors differ: lmfit={params_lmfit['n'].value}, new={params_new['n']}"
    )

    # Output patterns should match
    np.testing.assert_allclose(pattern_lmfit.y, pattern_new.y, rtol=1e-5)


def test_compare_normalize_fit_implementations_with_multiple_scattering(
    sample, f_squared_mean, incoherent_scattering
):
    """Compare implementations with multiple scattering enabled."""
    # Sample intensity is ~1e9, so add 1e11 to create significant offset
    sample_with_offset = Pattern(sample.x, sample.y + 1e11)

    params_lmfit, pattern_lmfit = normalize_fit_lmfit(
        sample_with_offset,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=5,
        multiple_scattering=True,
    )
    params_new, pattern_new = normalize_fit(
        sample_with_offset,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=5,
        multiple_scattering=True,
    )

    # Both should detect multiple scattering (value is scaled by n, so ~1e3)
    assert params_lmfit["multiple"].value > 1000
    assert params_new["multiple"] > 1000

    # Results should be very close (allowing some tolerance for iterative vs direct solver)
    assert np.isclose(params_lmfit["n"].value, params_new["n"], rtol=0.01, atol=0)
    assert np.isclose(params_lmfit["multiple"].value, params_new["multiple"], rtol=0.01, atol=0)
    np.testing.assert_allclose(pattern_lmfit.y, pattern_new.y, rtol=1e-3)


def test_compare_normalize_fit_implementations_with_container(
    sample, f_squared_mean, incoherent_scattering
):
    """Compare implementations with container scattering."""
    diamond_scattering = calculate_incoherent_scattering({"C": 1}, sample.x)
    sample_with_container = Pattern(sample.x, sample.y + 1e11 * diamond_scattering)

    params_lmfit, pattern_lmfit = normalize_fit_lmfit(
        sample_with_container,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=8,
        container_scattering=diamond_scattering,
    )
    params_new, pattern_new = normalize_fit(
        sample_with_container,
        f_squared_mean,
        incoherent_scattering,
        q_cutoff=8,
        container_scattering=diamond_scattering,
    )

    # Both should detect container scattering
    assert params_lmfit["n_container"].value > 100
    assert params_new["n_container"] > 100

    # Results should be very close (allowing some tolerance for iterative vs direct solver)
    assert np.isclose(params_lmfit["n"].value, params_new["n"], rtol=0.01, atol=0)
    assert np.isclose(
        params_lmfit["n_container"].value, params_new["n_container"], rtol=0.01, atol=0
    )
    np.testing.assert_allclose(pattern_lmfit.y, pattern_new.y, rtol=1e-3)

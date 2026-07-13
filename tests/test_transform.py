import os
import numpy as np
import pytest

from glassure import Pattern
from glassure.utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    convert_density_to_atoms_per_cubic_angstrom,
    extrapolate_to_zero_linear,
    calculate_s0,
)
from glassure.normalization import normalize
from glassure.transform import (
    calculate_sq,
    calculate_fr,
    calculate_gr,
    calculate_rdf,
    calculate_sq_from_fr,
    calculate_rdf,
    calculate_tr,
)

from . import unittest_data_path


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
def normalized_pattern(
    sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
):
    """Create normalized pattern for testing."""
    _, normalized = normalize(
        sample,
        atomic_density,
        f_squared_mean,
        f_mean_squared,
        incoherent_scattering,
    )
    return normalized


def test_calculate_sq(normalized_pattern, f_squared_mean, f_mean_squared, sample):
    """Test the calculate_sq function."""
    sq = calculate_sq(normalized_pattern, f_squared_mean, f_mean_squared)

    assert len(sq.x) == len(sample.x)
    assert len(sq.y) == len(sample.y)

    sq_mean = np.mean(sq.y[sq.x > 15])
    assert np.isclose(sq_mean, 1.0, atol=0.2)


def test_calculate_fr(sq):
    """Test the calculate_fr function with different methods and options."""
    # Test integral method without modification function
    fr = calculate_fr(sq)
    fr_mean = np.mean(fr.y[fr.x < 7])
    assert np.isclose(fr_mean, 0.0, atol=0.2)

    # Test integral method with modification function
    fr_mod = calculate_fr(sq, use_modification_fcn=True)
    fr_mod_mean = np.mean(fr_mod.y[fr_mod.x > 7])
    assert np.isclose(fr_mod_mean, 0.0, atol=0.2)
    assert np.array_equal(fr.x, fr_mod.x)
    assert not np.array_equal(fr.y, fr_mod.y)

    # Test FFT method without modification function
    fr_fft = calculate_fr(sq, method="fft")
    fr_fft_mod = calculate_fr(sq, use_modification_fcn=True, method="fft")
    fr_fft_mean = np.mean(fr_fft.y[fr_fft.x > 7])
    assert np.isclose(fr_fft_mean, 0.0, atol=0.2)

    # Test FFT method with modification function
    fr_fft_mod = calculate_fr(sq, use_modification_fcn=True, method="fft")
    fr_fft_mod_mean = np.mean(fr_fft_mod.y[fr_fft_mod.x > 7])
    assert np.isclose(fr_fft_mod_mean, 0.0, atol=0.2)
    assert np.array_equal(fr_fft.x, fr_fft_mod.x)
    assert not np.array_equal(fr_fft.y, fr_fft_mod.y)
    assert np.allclose(fr_mod.y, fr_fft_mod.y, atol=0.025)


@pytest.mark.parametrize("method", ["integral", "fft"])
def test_calculate_fr_lorch_modification_at_q_zero(sq, method):
    """The Lorch function must use its finite limiting value at Q=0."""
    sq_at_zero = sq.model_copy(deep=True)
    sq_at_zero.x[0] = 0.0

    fr = calculate_fr(sq_at_zero, use_modification_fcn=True, method=method)

    assert np.all(np.isfinite(fr.y))


def test_calculate_gr(sq, atomic_density):
    """Test the calculate_gr function."""
    fr = calculate_fr(sq, method="fft")

    gr = calculate_gr(fr, atomic_density)

    assert len(gr.x) == len(fr.x)
    assert len(gr.y) == len(fr.y)

    gr_mean = np.mean(gr.y[gr.x > 7])
    assert np.isclose(gr_mean, 1, atol=0.1)


def test_calculate_sq_from_fr(sq):
    """Test the calculate_sq_from_fr function."""
    fr = calculate_fr(sq)

    sq_from_fr = calculate_sq_from_fr(fr, sq.x)
    # the first few points are not very accurate, so we ignore them
    start_index = 10 
    assert np.allclose(sq.y[start_index:], sq_from_fr.y[start_index:], atol=0.12)

    sq_from_fr_fft = calculate_sq_from_fr(fr, sq.x, method="fft")
    assert np.allclose(sq_from_fr.y, sq_from_fr_fft.y, atol=0.05)


def test_calculate_sq_from_fr_with_modification_fcn(sq):
    """Test the calculate_sq_from_fr function with the modification function."""
    fr = calculate_fr(sq, use_modification_fcn=True)
    q = sq.x
    sq_from_fr = calculate_sq_from_fr(fr, q, use_modification_fcn=True)
    start_index = 10
    assert np.allclose(sq.y[start_index:], sq_from_fr.y[start_index:], atol=0.15)

    sq_from_fr_fft = calculate_sq_from_fr(fr, q, method="fft", use_modification_fcn=True)
    assert np.allclose(sq.y[start_index:], sq_from_fr_fft.y[start_index:], atol=0.15)


@pytest.mark.parametrize("method", ["integral", "fft"])
def test_calculate_sq_from_fr_lorch_modification_at_q_zero(sq, method):
    """The inverse transform must also remain finite at Q=0."""
    sq_at_zero = sq.model_copy(deep=True)
    sq_at_zero.x[0] = 0.0
    fr = calculate_fr(sq_at_zero, use_modification_fcn=True, method=method)

    sq_from_fr = calculate_sq_from_fr(
        fr, sq_at_zero.x, method=method, use_modification_fcn=True
    )

    assert np.all(np.isfinite(sq_from_fr.y))


def test_calculate_fr_then_sq_and_fr(sq):
    fr = calculate_fr(sq)
    sq_from_fr = calculate_sq_from_fr(fr, sq.x, method="fft")
    fr_from_sq = calculate_fr(sq_from_fr)
    assert np.allclose(fr.y, fr_from_sq.y, atol=0.2)


def test_calculate_rdf(sq, atomic_density):
    fr = calculate_fr(sq)
    gr = calculate_gr(fr, atomic_density)

    rdf = calculate_rdf(gr, atomic_density)

    assert np.allclose(rdf.y, 4 * np.pi * gr.x**2 * atomic_density * gr.y, atol=0.2)


def test_calculate_tr(sq, atomic_density):
    fr = calculate_fr(sq)
    gr = calculate_gr(fr, atomic_density)
    rdf = calculate_rdf(gr, atomic_density)
    tr = calculate_tr(gr, atomic_density)
    assert np.allclose(tr.y, rdf.y / gr.x, atol=0.2)

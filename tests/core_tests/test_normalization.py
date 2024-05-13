import os
import numpy as np

from glassure.core import Pattern
from glassure.core.utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    convert_density_to_atoms_per_cubic_angstrom,
)
from glassure.core.normalization import normalize, normalize_fit

from .. import unittest_data_path

data_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
bkg_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


def test_normalize():
    data = Pattern.from_file(data_path)
    bkg = Pattern.from_file(bkg_path)

    sample = data - bkg
    sample = sample.limit(1, 15)

    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 2.9
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)

    f_squared_mean = calculate_f_squared_mean(composition, sample.x)
    f_mean_squared = calculate_f_mean_squared(composition, sample.x)
    incoherent_scattering = calculate_incoherent_scattering(composition, sample.x)

    n, _ = normalize(
        sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
    )
    assert n > 0


def test_normalize_fit():
    data = Pattern.from_file(data_path)
    bkg = Pattern.from_file(bkg_path)

    sample = data - bkg
    sample = sample.limit(1, 20)

    composition = {"Mg": 2, "Si": 1, "O": 4}

    f_squared_mean = calculate_f_squared_mean(composition, sample.x)
    incoherent_scattering = calculate_incoherent_scattering(composition, sample.x)

    params_1, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, multiple_scattering=False
    )
    params_2, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, multiple_scattering=True
    )
    params_3, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, correct_diamond=True
    )

    assert params_1["n"].value != params_2["n"].value
    assert params_1["n"].value != params_3["n"].value
    assert params_2["multiple"].value > 0
    assert params_3["n_diamond"].value > 0

    params_4, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=5
    )
    assert params_4["n"].value != params_1["n"].value


def test_compare_normalize_and_normalize_fit():
    data = Pattern.from_file(data_path)
    bkg = Pattern.from_file(bkg_path)

    sample = data - bkg
    sample = sample.limit(1, 15)

    composition = {"Mg": 2, "Si": 1, "O": 4}
    density = 2.9
    atomic_density = convert_density_to_atoms_per_cubic_angstrom(composition, density)

    f_squared_mean = calculate_f_squared_mean(composition, sample.x)
    f_mean_squared = calculate_f_mean_squared(composition, sample.x)
    incoherent_scattering = calculate_incoherent_scattering(composition, sample.x)

    n_normalize, _ = normalize(
        sample, atomic_density, f_squared_mean, f_mean_squared, incoherent_scattering
    )
    p_normalize_fit, _ = normalize_fit(
        sample, f_squared_mean, incoherent_scattering, q_cutoff=3
    )
    assert np.isclose(n_normalize, p_normalize_fit["n"].value, rtol=1e-2)

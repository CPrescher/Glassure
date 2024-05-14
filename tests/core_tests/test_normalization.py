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
from glassure.core.scattering_factors import calculate_coherent_scattering_factor

from .. import unittest_data_path

data_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
bkg_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


class TestNormalization:
    def setup_method(self):
        self.data = Pattern.from_file(data_path)
        self.bkg = Pattern.from_file(bkg_path)

        self.sample = self.data - self.bkg
        self.sample = self.sample.limit(1, 15)

        self.composition = {"Mg": 2, "Si": 1, "O": 4}
        self.density = 2.9
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)

        self.f_squared_mean = calculate_f_squared_mean(self.composition, self.sample.x)
        self.f_mean_squared = calculate_f_mean_squared(self.composition, self.sample.x)
        self.incoherent_scattering = calculate_incoherent_scattering(self.composition, self.sample.x)

    def test_normalize(self):
        n, _ = normalize(
            self.sample,
            self.atomic_density,
            self.f_squared_mean,
            self.f_mean_squared,
            self.incoherent_scattering,
        )
        assert n > 0


    def test_normalize_fit(self):
        params_1, _ = normalize_fit(
            self.sample, self.f_squared_mean, self.incoherent_scattering, multiple_scattering=False
        )
        params_2, _ = normalize_fit(
            self.sample, self.f_squared_mean, self.incoherent_scattering, multiple_scattering=True
        )
        diamond_scattering = calculate_coherent_scattering_factor("C", self.sample.x)
        params_3, _ = normalize_fit(
            self.sample,
            self.f_squared_mean,
            self.incoherent_scattering,
            container_scattering=diamond_scattering,
        )

        assert params_1["n"].value != params_2["n"].value
        assert params_1["n"].value != params_3["n"].value
        assert params_2["multiple"].value > 0
        assert params_3["n_container"].value > 0

        params_4, _ = normalize_fit(
            self.sample, self.f_squared_mean, self.incoherent_scattering, q_cutoff=5
        )
        assert params_4["n"].value != params_1["n"].value

    def test_compare_normalize_and_normalize_fit(self):
        n_normalize, normalized_pattern_1 = normalize(
            self.sample,
            self.atomic_density,
            self.f_squared_mean,
            self.f_mean_squared,
            self.incoherent_scattering,
        )
        p_normalize_fit, normalized_pattern_2 = normalize_fit(
            self.sample, self.f_squared_mean, self.incoherent_scattering, q_cutoff=5
        )
        assert np.isclose(n_normalize, p_normalize_fit["n"].value, rtol=1e-2)
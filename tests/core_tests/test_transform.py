import os
import numpy as np

from glassure.core import Pattern
from glassure.core.utility import (
    calculate_f_squared_mean,
    calculate_f_mean_squared,
    calculate_incoherent_scattering,
    convert_density_to_atoms_per_cubic_angstrom,
)
from glassure.core.normalization import normalize
from glassure.core.transform import (
    calculate_sq,
    calculate_fr,
    calculate_gr,
    calculate_sq_from_fr,
)

from .. import unittest_data_path

data_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient.xy")
bkg_path = os.path.join(unittest_data_path, "Mg2SiO4_ambient_bkg.xy")


class TestTransform:
    def setup_method(self):
        # Setting up everything until the normalization of the data
        self.data = Pattern.from_file(data_path)
        self.bkg = Pattern.from_file(bkg_path)

        self.sample = self.data - self.bkg
        self.sample = self.sample.limit(1, 20)

        self.composition = {"Mg": 2, "Si": 1, "O": 4}
        self.density = 2.9
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(
            self.composition, self.density
        )

        self.f_squared_mean = calculate_f_squared_mean(self.composition, self.sample.x)
        self.f_mean_squared = calculate_f_mean_squared(self.composition, self.sample.x)
        self.incoherent_scattering = calculate_incoherent_scattering(
            self.composition, self.sample.x
        )

        _, self.normalized_pattern = normalize(
            self.sample,
            self.atomic_density,
            self.f_squared_mean,
            self.f_mean_squared,
            self.incoherent_scattering,
        )

    def test_calculate_sq(self):
        sq = calculate_sq(
            self.normalized_pattern, self.f_squared_mean, self.f_mean_squared
        )

        assert len(sq.x) == len(self.sample.x)
        assert len(sq.y) == len(self.sample.y)

        sq_mean = np.mean(sq.y[sq.x > 15])
        assert np.isclose(sq_mean, 1.0, atol=0.2)

    def test_calculate_fr(self):
        sq = calculate_sq(
            self.normalized_pattern, self.f_squared_mean, self.f_mean_squared
        )
        sq = sq.extend_to(0, 0)  # for a fft to work, the pattern needs to start at 0
        fr = calculate_fr(sq)

        fr_mean = np.mean(fr.y[fr.x < 7])
        assert np.isclose(fr_mean, 0.0, atol=0.2)

        fr_mod = calculate_fr(sq, use_modification_fcn=True)
        fr_mod_mean = np.mean(fr_mod.y[fr_mod.x > 7])
        assert np.isclose(fr_mod_mean, 0.0, atol=0.2)
        assert np.array_equal(fr.x, fr_mod.x)
        assert not np.array_equal(fr.y, fr_mod.y)

        fr_fft = calculate_fr(sq, method="fft")
        fr_fft_mean = np.mean(fr_fft.y[fr_fft.x > 7])
        assert np.isclose(fr_fft_mean, 0.0, atol=0.2)
        assert np.allclose(fr.y, fr_fft.y, atol=0.005)

        fr_fft_mod = calculate_fr(sq, use_modification_fcn=True, method="fft")
        fr_fft_mod_mean = np.mean(fr_fft_mod.y[fr_fft_mod.x > 7])
        assert np.isclose(fr_fft_mod_mean, 0.0, atol=0.2)
        assert np.array_equal(fr_fft.x, fr_fft_mod.x)
        assert not np.array_equal(fr_fft.y, fr_fft_mod.y)
        assert np.allclose(fr_mod.y, fr_fft_mod.y, atol=0.005)

    def test_calculate_gr(self):
        sq = calculate_sq(
            self.normalized_pattern, self.f_squared_mean, self.f_mean_squared
        )
        sq = sq.extend_to(0, 0)
        fr = calculate_fr(sq, method="fft")

        gr = calculate_gr(fr, self.atomic_density)

        assert len(gr.x) == len(fr.x)
        assert len(gr.y) == len(fr.y)

        gr_mean = np.mean(gr.y[gr.x > 7])
        assert np.isclose(gr_mean, 1, atol=0.1)

    def test_calculate_sq_from_fr(self):
        sq = calculate_sq(
            self.normalized_pattern, self.f_squared_mean, self.f_mean_squared
        )
        sq = sq.extend_to(0, 0)

        fr = calculate_fr(sq)

        sq_from_fr = calculate_sq_from_fr(fr, sq.x)
        assert np.allclose(sq.y, sq_from_fr.y, atol=0.3)

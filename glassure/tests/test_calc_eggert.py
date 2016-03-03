import os
import unittest
import numpy as np
import matplotlib.pyplot as plt

from core import Spectrum
from core.calc_eggert import calculate_effective_form_factors, calculate_atomic_number_sum, \
    calculate_incoherent_scattering, calculate_j, calculate_s_inf, calculate_alpha, \
    calculate_coherent_scattering, calculate_sq, calculate_fr, optimize_iq, \
    calculate_chi2_map, optimize_density_and_bkg_scaling

from core import convert_density_to_atoms_per_cubic_angstrom

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Argon_1GPa.chi')
bkg_path = os.path.join(unittest_data_path, 'Argon_1GPa_bkg.chi')


class CalcEggertTest(unittest.TestCase):
    def setUp(self):
        self.N = 1
        self.density = 1.9
        self.composition = {'Ar': 1}
        self.r = np.linspace(0.1, 10, 1000)

        data_spectrum = Spectrum.from_file(sample_path)
        bkg_spectrum = Spectrum.from_file(bkg_path)
        self.data_spectrum = Spectrum(data_spectrum.x / 10., data_spectrum.y)
        self.bkg_spectrum = Spectrum(bkg_spectrum.x / 10., bkg_spectrum.y)

        bkg_scaling = 0.57

        self.q_min = 0.3
        self.q_max = 9.0

        self.sample_spectrum = self.data_spectrum - bkg_scaling * self.bkg_spectrum
        self.sample_spectrum = self.sample_spectrum.limit(self.q_min, self.q_max).extend_to(0, 0)

    def test_calculate_atomic_number_sum(self):
        z_tot = calculate_atomic_number_sum({'O': 1})
        self.assertEqual(z_tot, 8)
        z_tot = calculate_atomic_number_sum({'Si': 1})
        self.assertEqual(z_tot, 14)
        self.assertEqual(calculate_atomic_number_sum({'Si': 1, 'O': 2}), 30)

    def test_calculate_effective_form_factor(self):
        composition = {'Si': 1, 'O': 2}
        q = np.linspace(0, 10, 1000)
        f_eff = calculate_effective_form_factors(composition, q)
        self.assertAlmostEqual(f_eff[0], 1.00034)
        self.assertAlmostEqual(f_eff[-1], 0.2303865)

    def test_calculate_incoherent_scattering(self):
        composition = {'Si': 1, 'O': 2}
        q = np.linspace(0, 10, 1000)
        inc = calculate_incoherent_scattering(composition, q)

        self.assertAlmostEqual(inc[0], -2.04068700e-02)
        self.assertAlmostEqual(inc[-1], 2.34904184e+01)

    def test_calculate_j(self):
        composition = {'Si': 1, 'O': 2}
        q = np.linspace(0, 10, 1000)
        inc = calculate_incoherent_scattering(composition, q)
        f_eff = calculate_effective_form_factors(composition, q)
        z_tot = calculate_atomic_number_sum(composition)

        j = calculate_j(inc, z_tot, f_eff)

        self.assertAlmostEqual(j[0], -2.26588893e-05)
        self.assertAlmostEqual(j[-1], 4.91738471e-01)

    def test_calculate_s_inf(self):
        composition = {'Si': 1, 'O': 2}
        q = np.linspace(0, 10, 1000)
        f_eff = calculate_effective_form_factors(composition, q)
        z_tot = calculate_atomic_number_sum(composition)

        s_inf = calculate_s_inf(composition, z_tot, f_eff, q)

        self.assertAlmostEqual(s_inf, 0.387305767285)

    def test_calculate_alpha(self):
        q = self.sample_spectrum.x

        inc = calculate_incoherent_scattering(self.composition, q)
        f_eff = calculate_effective_form_factors(self.composition, q)
        z_tot = calculate_atomic_number_sum(self.composition)
        s_inf = calculate_s_inf(self.composition, z_tot, f_eff, q)
        j = calculate_j(inc, z_tot, f_eff)

        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        alpha = calculate_alpha(self.sample_spectrum, z_tot, f_eff, s_inf, j, atomic_density)

        self.assertAlmostEqual(alpha, 0.150743212607, places=4)

    def test_calculate_coherent_scattering(self):
        q = self.sample_spectrum.x

        inc = calculate_incoherent_scattering(self.composition, q)
        f_eff = calculate_effective_form_factors(self.composition, q)
        z_tot = calculate_atomic_number_sum(self.composition)
        s_inf = calculate_s_inf(self.composition, z_tot, f_eff, q)
        j = calculate_j(inc, z_tot, f_eff)

        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        alpha = calculate_alpha(self.sample_spectrum, z_tot, f_eff, s_inf, j, atomic_density)

        coherent_pattern = calculate_coherent_scattering(self.sample_spectrum, alpha, self.N,
                                                         inc)

        self.assertAlmostEqual(coherent_pattern.y[-1], 36.521, places=3)

    def test_calculate_sq(self):
        q = self.sample_spectrum.x

        inc = calculate_incoherent_scattering(self.composition, q)
        f_eff = calculate_effective_form_factors(self.composition, q)
        z_tot = calculate_atomic_number_sum(self.composition)
        s_inf = calculate_s_inf(self.composition, z_tot, f_eff, q)
        j = calculate_j(inc, z_tot, f_eff)

        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        alpha = calculate_alpha(self.sample_spectrum, z_tot, f_eff, s_inf, j, atomic_density)

        coherent_pattern = calculate_coherent_scattering(self.sample_spectrum, alpha, self.N,
                                                         inc)

        sq_pattern = calculate_sq(coherent_pattern, self.N, z_tot, f_eff)

        self.assertAlmostEqual(sq_pattern.y[-1], 0.97, places=2)

    def test_calculate_fr(self):
        q = self.sample_spectrum.x

        inc = calculate_incoherent_scattering(self.composition, q)
        f_eff = calculate_effective_form_factors(self.composition, q)
        z_tot = calculate_atomic_number_sum(self.composition)
        s_inf = calculate_s_inf(self.composition, z_tot, f_eff, q)
        j = calculate_j(inc, z_tot, f_eff)

        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        alpha = calculate_alpha(self.sample_spectrum, z_tot, f_eff, s_inf, j, atomic_density)

        coherent_pattern = calculate_coherent_scattering(self.sample_spectrum, alpha, self.N,
                                                         inc)

        sq_pattern = calculate_sq(coherent_pattern, self.N, z_tot, f_eff)
        iq_pattern = Spectrum(sq_pattern.x, sq_pattern.y - s_inf)

        fr_pattern = calculate_fr(iq_pattern, r=np.arange(0, 14, 0.02))

        self.assertLess(np.mean(fr_pattern.limit(5, 20).y), 0.2)

    def test_optimize_iq(self):
        q = self.sample_spectrum.x

        inc = calculate_incoherent_scattering(self.composition, q)
        f_eff = calculate_effective_form_factors(self.composition, q)
        z_tot = calculate_atomic_number_sum(self.composition)
        s_inf = calculate_s_inf(self.composition, z_tot, f_eff, q)
        j = calculate_j(inc, z_tot, f_eff)

        atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        alpha = calculate_alpha(self.sample_spectrum, z_tot, f_eff, s_inf, j, atomic_density)

        coherent_pattern = calculate_coherent_scattering(self.sample_spectrum, alpha, self.N,
                                                         inc)

        sq_pattern = calculate_sq(coherent_pattern, self.N, z_tot, f_eff)
        iq_pattern = Spectrum(sq_pattern.x, sq_pattern.y - s_inf)
        iq_pattern_optimized = optimize_iq(iq_pattern, 2.4, 10, 0.026, j, s_inf)
        self.assertLess(np.abs(np.mean(iq_pattern_optimized.limit(5, 20).y)), 0.1)

    def test_calculate_chi2_map(self):
        densities = np.arange(0.02, 0.031, 0.002)
        bkg_scalings = np.arange(0.5, 0.6, 0.02)

        chi2_map = calculate_chi2_map(self.data_spectrum.limit(0.3, 9),
                                      self.bkg_spectrum.limit(0.3, 9),
                                      self.composition,
                                      densities=densities,
                                      bkg_scalings=bkg_scalings,
                                      r_cutoff=2.4)

        min_index = np.argmin(chi2_map)
        density_index, bkg_scaling_index = np.unravel_index(min_index, chi2_map.shape)

        self.assertAlmostEqual(densities[density_index], 0.026)
        self.assertAlmostEqual(bkg_scalings[bkg_scaling_index], 0.54)


    def test_optimize_density_and_bkg_scaling(self):
        density, _, bkg_scaling, _ = optimize_density_and_bkg_scaling(self.data_spectrum.limit(0.3, 9),
                                                                self.bkg_spectrum.limit(0.3, 9),
                                                                self.composition,
                                                                initial_density=0.03,
                                                                initial_bkg_scaling=0.3,
                                                                r_cutoff=2.28,
                                                                iterations=1)
        self.assertAlmostEqual(density, 0.025, places=3)
        self.assertAlmostEqual(bkg_scaling, 0.55, places=2)

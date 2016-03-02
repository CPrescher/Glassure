import os
import unittest
import numpy as np
import matplotlib.pyplot as plt

from core import Spectrum
from core.calc_eggert import calculate_effective_form_factors, calculate_atomic_number_sum, \
    calculate_incoherent_scattering, calculate_j, calculate_s_inf, calculate_alpha, \
    calculate_coherent_scattering, calculate_sq
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
        self.sample_spectrum = self.sample_spectrum.limit(self.q_min, self.q_max)

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

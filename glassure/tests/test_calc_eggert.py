import os
import unittest
import numpy as np

from core import Spectrum
from core.calc_eggert import calculate_effective_form_factors, calc_atomic_number_sum, calculate_incoherent_scattering, \
    calculate_j, calculate_s_inf

unittest_data_path = os.path.join(os.path.dirname(__file__), 'data')
sample_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient.xy')
bkg_path = os.path.join(unittest_data_path, 'Mg2SiO4_ambient_bkg.xy')


class CalcEggertTest(unittest.TestCase):
    def setUp(self):
        self.density = 2.9
        self.composition = {'Mg': 2, 'Si': 1, 'O': 4}
        self.r = np.linspace(0.1, 10, 1000)

        self.data_spectrum = Spectrum()
        self.data_spectrum.load(sample_path)

        self.bkg_spectrum = Spectrum()
        self.bkg_spectrum.load(bkg_path)

        self.sample_spectrum = self.data_spectrum - self.bkg_spectrum

    def test_calculate_atomic_number_sum(self):
        z_tot = calc_atomic_number_sum({'O': 1})
        self.assertEqual(z_tot, 8)
        z_tot = calc_atomic_number_sum({'Si': 1})
        self.assertEqual(z_tot, 14)
        self.assertEqual(calc_atomic_number_sum({'Si': 1, 'O': 2}), 30)

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
        z_tot = calc_atomic_number_sum(composition)

        j = calculate_j(inc, z_tot, f_eff)

        self.assertAlmostEqual(j[0], -2.26588893e-05)
        self.assertAlmostEqual(j[-1], 4.91738471e-01)

    def test_calculate_s_inf(self):
        composition = {'Si': 1, 'O': 2}
        q = np.linspace(0, 10, 1000)
        f_eff = calculate_effective_form_factors(composition, q)
        z_tot = calc_atomic_number_sum(composition)

        s_inf = calculate_s_inf(composition, z_tot, f_eff, q)

        self.assertAlmostEqual(s_inf, 0.387305767285)

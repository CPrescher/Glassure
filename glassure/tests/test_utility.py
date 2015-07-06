__author__ = 'Clemens Prescher'

import unittest
import numpy as np

from core.utility import normalize_elemental_abundances, convert_density_to_atoms_per_cubic_angstrom, \
    calculate_f_mean_squared, calculate_f_squared_mean, calculate_incoherent_scattering

class UtilityTest(unittest.TestCase):
    def test_normalize_elemental_abundances(self):
        composition = {'Si': 1, 'O':2}
        norm_composition = normalize_elemental_abundances(composition)
        self.assertEqual(norm_composition, {'Si': 1/3., 'O': 2/3.})

        composition = {'Na': 2, 'Si': 2, 'O':5}
        norm_composition = normalize_elemental_abundances(composition)
        self.assertEqual(norm_composition, {'Na': 2./9, 'Si': 2/9., 'O': 5/9.})

    def test_convert_density_to_atoms_per_cubic_angstrom(self):
        density = 2.2
        composition = {'Si': 1, 'O':2}
        density_au = convert_density_to_atoms_per_cubic_angstrom(composition, density)

        self.assertAlmostEqual(density_au, 0.0662, places=4)

    def test_calculate_f_mean_squared(self):
        q = np.linspace(0, 10)
        composition = {'Si': 1, 'O':2}

        f_mean_squared = calculate_f_mean_squared(composition, q)

        self.assertEqual(len(q), len(f_mean_squared))

        si_f = calculate_f_mean_squared({'Si':1}, q)**0.5
        o_f = calculate_f_mean_squared({'O':1}, q)**0.5

        f_mean_squared_hand = (1/3.*si_f+2/3.*o_f)**2

        self.assertTrue(np.array_equal(f_mean_squared, f_mean_squared_hand))

    def test_calculate_f_squared_mean(self):
        q = np.linspace(0, 10)
        composition = {'Si': 1, 'O':2}

        f_squared_mean= calculate_f_squared_mean(composition, q)

        self.assertEqual(len(q), len(f_squared_mean))

        si_f = calculate_f_squared_mean({'Si':1}, q)**0.5
        o_f = calculate_f_squared_mean({'O':1}, q)**0.5

        f_squared_mean_hand = 1/3.*si_f**2+2/3.*o_f**2

        self.assertTrue(np.array_equal(f_squared_mean, f_squared_mean_hand))

    def test_calculate_incoherent_scattering(self):
        q = np.linspace(0, 10)
        incoherent_scattering = calculate_incoherent_scattering({'Si':1, 'O':2}, q)

        self.assertEqual(len(q), len(incoherent_scattering))

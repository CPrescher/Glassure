# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
import numpy as np
from Spectrum import Spectrum

from GlassureUtility import convert_density_to_atoms_per_cubic_angstrom, calculate_incoherent_scattering, \
    calculate_f_mean_squared, calculate_f_squared_mean


class GlassureCalculator(object):
    def __init__(self, original_spectrum, background_spectrum, background_scaling, elemental_abundances, density,
                 r=np.linspace(0,10, 1000)):
        self.original_spectrum = original_spectrum
        self.background_spectrum = background_spectrum
        self.background_scaling = background_scaling
        self.sample_spectrum = self.original_spectrum - self.background_scaling * self.background_spectrum
        self.elemental_abundances = elemental_abundances
        self.density = density
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density)

        q, _ = self.original_spectrum.data
        self.incoherent_scattering = calculate_incoherent_scattering(elemental_abundances, q)
        self.f_mean_squared = calculate_f_mean_squared(elemental_abundances, q)
        self.f_squared_mean = calculate_f_squared_mean(elemental_abundances, q)

        self.sq_spectrum = None
        self.fr_spectrum = None
        self.gr_spectrum = None

        self.r = r
        self.calculate_transforms(r)

    def calculate_transforms(self, r):
        self.sq_spectrum = self.calc_sq()
        self.fr_spectrum = self.calc_fr(r)
        self.gr_spectrum = self.calc_gr()

    def update_density(self, density):
        self.density = density
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.elemental_abundances, density)
        self.calculate_transforms()

    def get_normalization_factor(self):
        raise NotImplementedError

    def calc_sq(self):
        raise NotImplementedError

    def calc_fr(self,r):
        raise NotImplementedError

    def calc_gr(self):
        raise NotImplementedError

    def optimize(self, r):
        raise NotImplementedError


class StandardCalculator(GlassureCalculator):
    def get_normalization_factor(self, attenuation_factor=0.001):
        q, intensity = self.sample_spectrum.data

        # calculate values for integrals
        # old version
        n1 = q ** 2 * ((self.f_squared_mean + self.incoherent_scattering) * np.exp(-attenuation_factor * q ** 2)) / \
             self.f_mean_squared
        n2 = q ** 2 * intensity * np.exp(-attenuation_factor * q ** 2) / self.f_mean_squared

        # calculate atomic scattering factor
        n = ((-2 * np.pi ** 2 * self.atomic_density + np.trapz(q, n1)) / np.trapz(q, n2))

        return n

    def calc_sq(self):
        n = self.get_normalization_factor()
        q, intensity = self.sample_spectrum.data
        # old version
        structure_factor = (n * intensity - self.incoherent_scattering) / self.f_mean_squared
        return Spectrum(q, structure_factor)

    def calc_fr(self, r=None):
        if r is None:
            r=self.r
        q, intensity = self.sq_spectrum.data
        modification = np.sin(q * np.pi / np.max(q)) / (q * np.pi / np.max(q))
        fr = 2.0 / np.pi * np.trapz(modification * q * (intensity - 1) *
                                    np.array(np.sin(np.mat(q).T * np.mat(r))).T, q)
        return Spectrum(r, fr)

    def calc_gr(self):
        r, f_r = self.fr_spectrum.data
        g_r = 1+f_r / (4.0 * np.pi * r * self.atomic_density)
        return Spectrum(r, g_r)

    def optimize(self, r, iterations=50, fcn_callback = None):

        for _ in range(iterations):
            q, sq_int = self.sq_spectrum.data
            r, fr_int = self.calc_fr(r).data
            delta_fr = fr_int+4*np.pi*r *self.atomic_density
            sq_optimized = np.ones(sq_int.shape)
            for ind, q_value in enumerate(q):
                sq_optimized[ind] = sq_int[ind]*(1-1./q_value*np.trapz(delta_fr * np.sin(q_value*r), r))

            self.sq_spectrum = Spectrum(q, sq_optimized)

            if fcn_callback is not None:
                self.fr_spectrum = self.calc_fr()
                self.gr_spectrum = self.calc_gr()

                fcn_callback(self.sq_spectrum, self.gr_spectrum)




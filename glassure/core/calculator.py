# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'
import numpy as np
from scipy import interpolate

from .spectrum import Spectrum
from .utility import convert_density_to_atoms_per_cubic_angstrom, calculate_incoherent_scattering, \
    calculate_f_mean_squared, calculate_f_squared_mean

from .calc import calculate_normalization_factor_raw, calculate_sq_raw, calculate_fr, calculate_gr_raw


class GlassureCalculator(object):
    def __init__(self, original_spectrum, background_spectrum, elemental_abundances, density,
                 r=np.linspace(0, 10, 1000)):
        self.original_spectrum = original_spectrum
        self.background_spectrum = background_spectrum
        self.sample_spectrum = self.original_spectrum - self.background_spectrum
        self.elemental_abundances = elemental_abundances
        self.density = density
        self.atomic_density = convert_density_to_atoms_per_cubic_angstrom(elemental_abundances, density)

        q, _ = self.sample_spectrum.data
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

    def calc_fr(self, r):
        raise NotImplementedError

    def calc_gr(self):
        raise NotImplementedError

    def optimize(self, r):
        raise NotImplementedError


class StandardCalculator(GlassureCalculator):
    def __init__(self, original_spectrum, background_spectrum, elemental_abundances, density,
                 r=np.linspace(0, 10, 1000), normalization_attenuation_factor=0.001, use_modification_fcn=False,
                 interpolation_method=None, interpolation_parameters=None):
        self.attenuation_factor = normalization_attenuation_factor
        self.use_modification_fcn = use_modification_fcn
        self.interpolation_method = interpolation_method
        self.interpolation_parameters = interpolation_parameters

        super(StandardCalculator, self).__init__(original_spectrum, background_spectrum,
                                                 elemental_abundances, density, r)

    def get_normalization_factor(self):
        return calculate_normalization_factor_raw(self.sample_spectrum,
                                                  self.atomic_density,
                                                  self.f_squared_mean,
                                                  self.f_mean_squared,
                                                  self.incoherent_scattering,
                                                  self.attenuation_factor)

    def calc_sq(self):
        n = self.get_normalization_factor()
        q, structure_factor = calculate_sq_raw(self.sample_spectrum,
                                                self.f_squared_mean,
                                                self.f_mean_squared,
                                                self.incoherent_scattering,
                                                n).data
        # get q spacing and interpolate linearly to zero:
        if self.interpolation_method is None:
            return Spectrum(q, structure_factor)
        else:
            step = q[1] - q[0]
            q_low = np.arange(step, min(q), step)
            if self.interpolation_method == 'linear':
                sq_low = structure_factor[0] / q[0] * q_low
            elif self.interpolation_method == 'spline':
                q_low_cutoff = np.arange(step, self.interpolation_parameters['cutoff'], step)
                intensity_low_cutoff = np.zeros(q_low_cutoff.shape)

                ind_to_q_max = np.where(q <= self.interpolation_parameters['q_max'])
                q_spline = np.concatenate((q_low_cutoff, q[ind_to_q_max]))
                int_spline = np.concatenate((intensity_low_cutoff, structure_factor[ind_to_q_max]))

                tck = interpolate.splrep(q_spline, int_spline)

                sq_low = interpolate.splev(q_low, tck)

            return Spectrum(np.concatenate((q_low, q)),
                            np.concatenate((sq_low, structure_factor)))

    def calc_fr(self, r=None):
        if r is None:
            r = self.r
        return calculate_fr(self.sq_spectrum, r, self.use_modification_fcn)

    def calc_gr(self):
        return calculate_gr_raw(self.fr_spectrum, self.atomic_density)

    def optimize(self, r, iterations=50, fcn_callback=None, callback_period=5, attenuation_factor=1):
        import time

        t1 = time.time()
        for iteration in range(iterations):
            q, sq_int = self.sq_spectrum.data
            r, fr_int = self.calc_fr(r).data
            delta_fr = fr_int + 4 * np.pi * r * self.atomic_density

            in_integral = np.array(np.sin(np.mat(q).T * np.mat(r))) * delta_fr
            integral = np.trapz(in_integral, r) / attenuation_factor
            sq_optimized = sq_int * (1 - 1. / q * integral)

            self.sq_spectrum = Spectrum(q, sq_optimized)

            if fcn_callback is not None and iteration % 5 == 0:
                self.fr_spectrum = self.calc_fr()
                self.gr_spectrum = self.calc_gr()

                fcn_callback(self.sq_spectrum, self.gr_spectrum)

        print "Optimization took {}".format(time.time() - t1)

# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import numpy as np

from .Spectrum import Spectrum
from .HelperModule import Observable
from GlassureCalculator import StandardCalculator
from DensityOpimizitation import DensityOptimizer


class GlassureModel(Observable):
    def __init__(self):
        super(GlassureModel, self).__init__()
        self.original_spectrum = Spectrum()
        self.background_spectrum = Spectrum()
        self.background_scaling = 1.0
        self.background_offset = 0
        self.sq_spectrum = Spectrum()
        self.gr_spectrum = Spectrum()

        self.composition = {}
        self.density = 2.2
        self.density_error = None
        self.q_min = 0.0
        self.q_max = 10.0
        self.r_cutoff = 1.0
        self.r_min = 0.5
        self.r_max = 10

    def load_data(self, filename):
        self.original_spectrum.load(filename)
        self.calculate_spectra()

    def load_bkg(self, filename):
        self.background_spectrum.load(filename)
        self.calculate_spectra()

    def set_bkg_scale(self, scaling):
        self.background_scaling = scaling
        self.calculate_spectra()

    def get_background_spectrum(self):
        x, y = self.background_spectrum.data
        return Spectrum(x, self.background_offset + self.background_scaling * y)

    def set_bkg_offset(self, offset):
        self.background_offset = offset
        self.calculate_spectra()

    def set_smooth(self, value):
        self.original_spectrum.set_smoothing(value)
        self.background_spectrum.set_smoothing(value)
        self.calculate_spectra()

    def update_parameter(self, composition, density, q_min, q_max, r_cutoff, r_min, r_max):
        self.composition = composition
        self.density = density
        self.q_min = q_min
        self.q_max = q_max
        self.r_cutoff = r_cutoff
        self.r_min = r_min
        self.r_max = r_max
        self.calculate_spectra()

    def calculate_spectra(self):
        if len(self.composition) != 0:
            self.glassure_calculator = StandardCalculator(
                original_spectrum=self.limit_spectrum(self.original_spectrum, self.q_min, self.q_max),
                background_spectrum=self.limit_spectrum(self.background_spectrum, self.q_min, self.q_max),
                background_scaling=self.background_scaling,
                elemental_abundances=self.composition,
                density=self.density,
                r = np.linspace(self.r_min, self.r_max, 1000)
            )
            self.sq_spectrum = self.glassure_calculator.sq_spectrum
            self.fr_spectrum = self.glassure_calculator.fr_spectrum
            self.gr_spectrum = self.glassure_calculator.gr_spectrum
        self.notify()

    def optimize_sq(self, iterations=50, fcn_callback=None):
        self.glassure_calculator.optimize(np.linspace(0, self.r_cutoff, np.round(self.r_cutoff*100)),
                                          iterations=iterations, fcn_callback=fcn_callback)
        self.glassure_calculator.fr_spectrum = self.glassure_calculator.calc_fr()
        self.glassure_calculator.gr_spectrum = self.glassure_calculator.calc_gr()

        self.sq_spectrum = self.glassure_calculator.sq_spectrum
        self.fr_spectrum = self.glassure_calculator.fr_spectrum
        self.gr_spectrum = self.glassure_calculator.gr_spectrum
        self.notify()

    def optimize_density_and_scaling(self, iterations):
        optimizer = DensityOptimizer(
            original_spectrum=self.limit_spectrum(self.original_spectrum, self.q_min, self.q_max),
            background_spectrum=self.limit_spectrum(self.background_spectrum, self.q_min, self.q_max),
            initial_background_scaling=self.background_scaling,
            elemental_abundances=self.composition,
            initial_density=self.density,
            r_cutoff=self.r_cutoff,
            r = np.linspace(self.r_min, self.r_max, 1000)
        )

        optimizer.optimize(iterations)




    @staticmethod
    def limit_spectrum(spectrum, q_min, q_max):
        q, intensity = spectrum.data
        return Spectrum(q[np.where((q_min < q) & (q < q_max))],
                        intensity[np.where((q_min < q) & (q < q_max))])




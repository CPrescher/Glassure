# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import numpy as np
from lmfit import Parameters, minimize
from PyQt4 import QtGui

from .Spectrum import Spectrum
from .HelperModule import Observable
from GlassureCalculator import StandardCalculator
from DensityOptimization import DensityOptimizer
from .GlassureUtility import calculate_incoherent_scattering, convert_density_to_atoms_per_cubic_angstrom


class GlassureModel(Observable):
    def __init__(self):
        super(GlassureModel, self).__init__()
        # initialize all spectra
        self.original_spectrum = Spectrum()
        self._background_spectrum = Spectrum()

        self.diamond_background_spectrum = None

        self.sq_spectrum = Spectrum()
        self.gr_spectrum = Spectrum()

        # initialize all parameters
        self.composition = {}
        self.density = 2.2
        self.density_error = None
        self.q_min = 0.0
        self.q_max = 10.0
        self.r_cutoff = 1.0
        self.r_min = 0.5
        self.r_max = 10

        # initialize all Flags
        self.use_modification_fcn = True
        self.interpolation_method = None
        self.interpolation_parameters = None

    def load_data(self, filename):
        self.original_spectrum.load(filename)
        self.calculate_spectra()

    def load_bkg(self, filename):
        self.background_spectrum.load(filename)
        self.calculate_spectra()

    @property
    def background_spectrum(self):
        if self.diamond_background_spectrum is None:
            return self._background_spectrum
        return self._background_spectrum+self.diamond_background_spectrum

    def get_background_spectrum(self):
        x, y = self.background_spectrum.data
        return Spectrum(x, y)

    @property
    def background_scaling(self):
        return self._background_spectrum.scaling

    @background_scaling.setter
    def background_scaling(self, new_value):
        self._background_spectrum.scaling = new_value
        self.calculate_spectra()

    def set_smooth(self, value):
        self.original_spectrum.set_smoothing(value)
        self._background_spectrum.set_smoothing(value)
        self.calculate_spectra()

    def update_parameter(self, composition, density, q_min, q_max, r_cutoff, r_min, r_max, use_modification_fcn=False,
                         interpolation_method=None, interpolation_parameters=None):
        print "update"
        self.composition = composition
        self.density = density

        self.q_min = q_min
        self.q_max = q_max

        self.r_cutoff = r_cutoff
        self.r_min = r_min
        self.r_max = r_max

        self.use_modification_fcn = use_modification_fcn
        self.interpolation_method = interpolation_method
        self.interpolation_parameters = interpolation_parameters

        self.calculate_spectra()

    def calculate_spectra(self):
        if len(self.composition) != 0:
            self.glassure_calculator = StandardCalculator(
                original_spectrum=self.limit_spectrum(self.original_spectrum, self.q_min, self.q_max),
                background_spectrum=self.limit_spectrum(self.background_spectrum, self.q_min, self.q_max),
                elemental_abundances=self.composition,
                density=self.density,
                r=np.linspace(self.r_min, self.r_max, 1000),
                use_modification_fcn=self.use_modification_fcn,
                interpolation_method=self.interpolation_method,
                interpolation_parameters=self.interpolation_parameters
            )
            self.sq_spectrum = self.glassure_calculator.sq_spectrum
            self.fr_spectrum = self.glassure_calculator.fr_spectrum
            self.gr_spectrum = self.glassure_calculator.gr_spectrum
        self.notify()

    def optimize_sq(self, iterations=50, fcn_callback=None, attenuation_factor=1):
        self.glassure_calculator.optimize(np.linspace(0, self.r_cutoff, np.round(self.r_cutoff * 100)),
                                          iterations=iterations, fcn_callback=fcn_callback,
                                          attenuation_factor=attenuation_factor)
        self.glassure_calculator.fr_spectrum = self.glassure_calculator.calc_fr()
        self.glassure_calculator.gr_spectrum = self.glassure_calculator.calc_gr()

        self.sq_spectrum = self.glassure_calculator.sq_spectrum
        self.fr_spectrum = self.glassure_calculator.fr_spectrum
        self.gr_spectrum = self.glassure_calculator.gr_spectrum
        self.notify()

    def optimize_density_and_scaling2(self, density_min, density_max, bkg_min, bkg_max, iterations, output_txt=None):
        optimizer = DensityOptimizer(
            original_spectrum=self.limit_spectrum(self.original_spectrum, self.q_min, self.q_max),
            background_spectrum=self.limit_spectrum(self.background_spectrum, self.q_min, self.q_max),
            initial_background_scaling=self.background_scaling,
            elemental_abundances=self.composition,
            initial_density=self.density,
            r_cutoff=self.r_cutoff,
            r=np.linspace(self.r_min, self.r_max, 1000),
            density_min=density_min,
            density_max=density_max,
            bkg_min=bkg_min,
            bkg_max=bkg_max,
            use_modification_fcn=self.use_modification_fcn,
            interpolation_method=self.interpolation_method,
            interpolation_parameters=self.interpolation_parameters,
            output_txt=output_txt
        )

        optimizer.optimize(iterations)

    def optimize_density_and_scaling(self, density_min, density_max, bkg_min, bkg_max, iterations,
                                      callback_fcn = None, output_txt=None):
        params = Parameters()
        params.add("density", value=self.density, min=density_min, max=density_max)
        params.add("background_scaling", value=self.background_scaling, min=bkg_min, max=bkg_max)

        self.iteration = 0

        def optimization_fcn(params):
            density = params['density'].value
            background_scaling = params['background_scaling'].value

            self.background_spectrum.scaling = background_scaling
            self.calculate_spectra()
            self.optimize_sq(iterations,fcn_callback=callback_fcn)

            r, fr = self.limit_spectrum(self.fr_spectrum, 0, self.r_cutoff).data

            output = (-fr - 4 * np.pi * convert_density_to_atoms_per_cubic_angstrom(self.composition, density) *
                      r) ** 2

            self.write_output(u'{} X: {:.3f} Den: {:.3f}'.format(self.iteration, np.sum(output)/(r[1]-r[0]), density))
            self.iteration+=1
            return output

        minimize(optimization_fcn, params)
        self.write_fit_results(params)


    def write_output(self, msg, output_txt=None):
        if output_txt is None:
            print msg
        else:
            previous_txt = str(output_txt.toPlainText())
            new_txt = previous_txt + "\n" + str(msg)
            output_txt.setPlainText(new_txt)
            # QtGui.QApplication.processEvents()
            output_txt.verticalScrollBar().setValue(output_txt.verticalScrollBar().maximum())
            QtGui.QApplication.processEvents()
            output_txt.verticalScrollBar().setValue(output_txt.verticalScrollBar().maximum())
            QtGui.QApplication.processEvents()

    def write_fit_results(self, params):
        output =  '\nFit Results:\n'
        output += '-Background Scaling:\n  % .3g +/- %.3g\n' % (params['background_scaling'].value,
                                                              params['background_scaling'].stderr)
        output += '-Density:\n  % .3g +/- %.3g\n' % (params['density'].value,
                                                   params['density'].stderr)
        self.write_output(output)

    @staticmethod
    def limit_spectrum(spectrum, q_min, q_max):
        q, intensity = spectrum.data
        return Spectrum(q[np.where((q_min < q) & (q < q_max))],
                        intensity[np.where((q_min < q) & (q < q_max))])

    def set_diamond_content(self, content_value):
        if content_value is 0:
            self.diamond_background_spectrum = None
            self.calculate_spectra()
            return

        q, _ = self.background_spectrum.data
        int = calculate_incoherent_scattering({'C':1}, q)*content_value
        self.diamond_background_spectrum = Spectrum(q, int)
        self.calculate_spectra()

    def optimize_diamond_content(self, diamond_content = 0, callback_fcn = None):
        params = Parameters()
        if diamond_content == 0:
            diamond_content = 20
        params.add("content", value=diamond_content, min=0)

        def optimization_fcn(params):
            diamond_content = params['content'].value
            self.set_diamond_content(diamond_content)
            low_r_spectrum = self.limit_spectrum(self.gr_spectrum, 0, self.r_cutoff)
            if callback_fcn is not None:
                callback_fcn(diamond_content)
            return low_r_spectrum.data[1]

        result = minimize(optimization_fcn, params)
        print result







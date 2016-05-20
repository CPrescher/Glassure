# -*- coding: utf8 -*-

import numpy as np
from ..qt import QtGui
from lmfit import Parameters, minimize, report_fit

from core.calculator import StandardCalculator
from core.utility import convert_density_to_atoms_per_cubic_angstrom


class DensityOptimizer(object):
    def __init__(self,
                 original_spectrum, background_spectrum, initial_background_scaling,
                 elemental_abundances, initial_density,
                 density_min, density_max, bkg_min, bkg_max, r_cutoff,
                 use_modification_fcn=False, interpolation_method=None,interpolation_parameters=None, r=np.linspace(0, 10, 1000),
                 output_txt=None):
        self.original_spectrum = original_spectrum
        self.background_spectrum = background_spectrum
        self.background_scaling = initial_background_scaling
        self.elemental_abundances = elemental_abundances
        self.density = initial_density
        self.r = r
        self.minimization_r = np.linspace(0, r_cutoff, r_cutoff * 100)
        self.r_cutoff = r_cutoff

        self.bkg_min = bkg_min
        self.bkg_max = bkg_max
        self.density_min = density_min
        self.density_max = density_max
        self.use_modification_fcn = use_modification_fcn
        self.interpolation_method = interpolation_method
        self.interpolation_parameters = interpolation_parameters
        self.output_txt = output_txt
        self.iteration = 1

    def optimize(self, optimization_iterations=10,  fcn_callback=None):
        params = Parameters()
        params.add("density", value=self.density, min=self.density_min, max=self.density_max)
        params.add("background_scaling", value=self.background_scaling, min=self.bkg_min, max=self.bkg_max)

        def fcn_optimization(params):
            density = params['density'].value
            background_scaling = params['background_scaling'].value

            self.background_spectrum.scaling = background_scaling
            calculator = StandardCalculator(
                original_spectrum=self.original_spectrum,
                background_spectrum=self.background_spectrum,
                composition=self.elemental_abundances,
                density=density,
                r=self.r,
                interpolation_method=self.interpolation_method,
                interpolation_parameters=self.interpolation_parameters,
                use_modification_fcn=self.use_modification_fcn
            )
            calculator.optimize_sq(
                r_cutoff=self.minimization_r,
                iterations=optimization_iterations
            )

            if fcn_callback is not None:
                fr_spectrum = calculator.calc_fr()
                gr_spectrum = calculator.calc_gr()
                fcn_callback(background_scaling, density, fr_spectrum, gr_spectrum)

            r, fr = calculator.calc_fr(self.minimization_r).data

            output = (-fr - 4 * np.pi * convert_density_to_atoms_per_cubic_angstrom(self.elemental_abundances, density) *
                    self.minimization_r) ** 2


            self.write_output(u'{} X: {:.3f} Den: {:.3f}'.format(self.iteration, np.sum(output)/(r[1]-r[0]), density))
            self.iteration+=1
            return output

        self.output_txt.setPlainText('')
        minimize(fcn_optimization, params)
        self.write_fit_result(params)
        report_fit(params)

    def write_output(self, msg):
        if self.output_txt is None:
            print(msg)
        else:
            previous_txt = str(self.output_txt.toPlainText())
            new_txt = previous_txt + "\n" + str(msg)
            self.output_txt.setPlainText(new_txt)
            # QtGui.QApplication.processEvents()
            self.output_txt.verticalScrollBar().setValue(self.output_txt.verticalScrollBar().maximum())
            QtGui.QApplication.processEvents()
            self.output_txt.verticalScrollBar().setValue(self.output_txt.verticalScrollBar().maximum())
            QtGui.QApplication.processEvents()

    def write_fit_result(self, params):
        output =  '\nFit Results:\n'
        output += '-Background Scaling:\n  % .3g +/- %.3g\n' % (params['background_scaling'].value,
                                                              params['background_scaling'].stderr)
        output += '-Density:\n  % .3g +/- %.3g\n' % (params['density'].value,
                                                   params['density'].stderr)
        self.write_output(output)

__author__ = 'clemens'
import numpy as np
from lmfit import Parameters, minimize, report_fit
from Models.GlassureCalculator import StandardCalculator
from Models.GlassureUtility import convert_density_to_atoms_per_cubic_angstrom

class DensityOptimizer(object):
    def __init__(self, original_spectrum, background_spectrum, initial_background_scaling,
                 elemental_abundances, initial_density,
                 r_cutoff, r=np.linspace(0, 10, 1000)):

        self.original_spectrum = original_spectrum
        self.background_spectrum = background_spectrum
        self.background_scaling = initial_background_scaling
        self.elemental_abundances = elemental_abundances
        self.density = initial_density
        self.r = r
        self.minimization_r = np.linspace(0, r_cutoff, r_cutoff*100)
        self.r_cutoff = r_cutoff

    def optimize(self, optimization_iterations=10, fcn_callback=None):

        params = Parameters()
        params.add("density", value=self.density, min=0.5, max=3)
        params.add("background_scaling", value=self.background_scaling, min=0, vary=True)

        print self.elemental_abundances

        def fcn_optimization(params):
            density = params['density'].value
            background_scaling = params['background_scaling'].value

            calculator = StandardCalculator(
                original_spectrum=self.original_spectrum,
                background_spectrum=self.background_spectrum,
                background_scaling=background_scaling,
                elemental_abundances=self.elemental_abundances,
                density=density,
                r=self.r
            )
            calculator.optimize(
                r=self.minimization_r,
                iterations=optimization_iterations
            )
            if fcn_callback is not None:
                fr_spectrum = calculator.calc_fr()
                gr_spectrum = calculator.calc_gr()
                fcn_callback(background_scaling, density, fr_spectrum, gr_spectrum)
            r, fr = calculator.calc_fr(self.minimization_r).data

            test= (fr+4*np.pi*convert_density_to_atoms_per_cubic_angstrom(self.elemental_abundances, density)*\
                    self.minimization_r)
            return np.array([np.trapz(test**2, r)]*2)


        minimize(fcn_optimization, params)
        report_fit(params)







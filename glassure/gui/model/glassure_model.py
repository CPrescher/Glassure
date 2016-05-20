# -*- coding: utf8 -*-

import numpy as np
from lmfit import Parameters, minimize
from ..qt import QtGui, QtCore, Signal

from core.pattern import Pattern
from .density_optimization import DensityOptimizer
from core.utility import calculate_incoherent_scattering, convert_density_to_atoms_per_cubic_angstrom
from core import calculate_sq, calculate_gr, calculate_fr
from core.optimization import optimize_sq


class GlassureModel(QtCore.QObject):
    data_changed = Signal()
    sq_changed = Signal(Pattern)
    fr_changed = Signal(Pattern)
    gr_changed = Signal(Pattern)

    def __init__(self):
        super(GlassureModel, self).__init__()

        # initialize all spectra
        self.original_spectrum = Pattern()
        self._background_spectrum = Pattern()

        self.diamond_background_spectrum = None

        self._sq_spectrum = None
        self._fr_spectrum = None
        self._gr_spectrum = None

        # initialize all parameters
        self._composition = {}

        self._density = 2.2
        self.density_error = None

        self._q_min = 0.0
        self._q_max = 10.0

        self._r_min = 0.5
        self._r_max = 10
        self.r_step = 0.01

        self.r_cutoff = 1.4

        # initialize all Flags
        self._use_modification_fcn = False

        self.interpolation_method = None
        self.interpolation_parameters = None

    def load_data(self, filename):
        self.original_spectrum.load(filename)
        self.calculate_transforms()

    def load_bkg(self, filename):
        self.background_spectrum.load(filename)
        self.calculate_transforms()

    @property
    def atomic_density(self):
        if len(self.composition):
            return convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        return 0

    @property
    def background_spectrum(self):
        if self.diamond_background_spectrum is None:
            return self._background_spectrum
        return self._background_spectrum + self.diamond_background_spectrum

    def get_background_spectrum(self):
        x, y = self.background_spectrum.data
        return Pattern(x, y)

    @property
    def background_scaling(self):
        return self._background_spectrum.scaling

    @background_scaling.setter
    def background_scaling(self, new_value):
        self._background_spectrum.scaling = new_value
        self.calculate_transforms()

    @property
    def composition(self):
        return self._composition

    @composition.setter
    def composition(self, new_composition):
        self._composition = new_composition
        self.calculate_transforms()

    @property
    def density(self):
        return self._density

    @density.setter
    def density(self, new_density):
        self._density = new_density
        self.calculate_transforms()

    @property
    def q_min(self):
        return self._q_min

    @q_min.setter
    def q_min(self, new_q_min):
        self._q_min = new_q_min
        self.calculate_transforms()

    @property
    def q_max(self):
        return self._q_max

    @q_max.setter
    def q_max(self, new_q_max):
        self._q_max = new_q_max
        self.calculate_transforms()

    @property
    def r_min(self):
        return self._r_min

    @r_min.setter
    def r_min(self, new_r_min):
        self._r_min = new_r_min
        self.calculate_transforms()

    @property
    def r_max(self):
        return self._r_max

    @r_max.setter
    def r_max(self, new_r_max):
        self._r_max = new_r_max
        self.calculate_transforms()

    @property
    def use_modification_fcn(self):
        return self._use_modification_fcn

    @use_modification_fcn.setter
    def use_modification_fcn(self, value):
        self._use_modification_fcn = value
        self.calculate_transforms()

    @property
    def sq_spectrum(self):
        return self._sq_spectrum

    @sq_spectrum.setter
    def sq_spectrum(self, new_sq):
        self._sq_spectrum = new_sq
        self.sq_changed.emit(new_sq)

    @property
    def fr_spectrum(self):
        return self._fr_spectrum

    @fr_spectrum.setter
    def fr_spectrum(self, new_fr):
        self._fr_spectrum = new_fr
        self.fr_changed.emit(new_fr)

    @property
    def gr_spectrum(self):
        return self._gr_spectrum

    @gr_spectrum.setter
    def gr_spectrum(self, new_gr):
        self._gr_spectrum = new_gr
        self.gr_changed.emit(new_gr)

    def set_smooth(self, value):
        self.original_spectrum.set_smoothing(value)
        self._background_spectrum.set_smoothing(value)
        self.calculate_transforms()

    def update_parameter(self, composition, density, q_min, q_max, r_cutoff, r_min=0, r_max=10,
                         use_modification_fcn=False, interpolation_method=None, interpolation_parameters=None):
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

        self.calculate_transforms()

    def calculate_transforms(self):
        if len(self.composition) != 0 and \
                        self.original_spectrum is not None and \
                        self.background_spectrum is not None:

            self.calculate_sq()
            self.calculate_fr()
            self.calculate_gr()
        self.data_changed.emit()

    def calculate_sq(self):
        self.sq_spectrum = calculate_sq((self.original_spectrum - self.background_spectrum). \
                                        limit(self.q_min, self.q_max),
                                        density=self.density,
                                        composition=self.composition)

    def calculate_fr(self):
        self.fr_spectrum = calculate_fr(self.sq_spectrum,
                                        r=np.arange(self.r_min, self.r_max + self.r_step * 0.5, self.r_step),
                                        use_modification_fcn=self.use_modification_fcn)

    def calculate_gr(self):
        self.gr_spectrum = calculate_gr(self.fr_spectrum, self.density, self.composition)


    def optimize_sq(self, iterations=50, fcn_callback=None, attenuation_factor=1, use_modification_fcn=False):
        self.sq_spectrum = optimize_sq(self.sq_spectrum, self.r_cutoff,
                                       iterations = iterations,
                                       atomic_density = convert_density_to_atoms_per_cubic_angstrom(self.composition,
                                                                                                    self.density),
                                       use_modification_fcn=use_modification_fcn,
                                       attenuation_factor= attenuation_factor,
                                       fcn_callback=fcn_callback)
        self.calculate_fr()
        self.calculate_gr()
        self.data_changed.emit()

    def optimize_density_and_scaling2(self, density_min, density_max, bkg_min, bkg_max, iterations, output_txt=None):
        optimizer = DensityOptimizer(
            original_spectrum=self.original_spectrum.limit(self.q_min, self.q_max),
            background_spectrum=self.background_spectrum.limit(self.q_min, self.q_max),
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
                                     callback_fcn=None, output_txt=None):
        params = Parameters()
        params.add("density", value=self.density, min=density_min, max=density_max)
        params.add("background_scaling", value=self.background_scaling, min=bkg_min, max=bkg_max)

        self.iteration = 0

        def optimization_fcn(params):
            density = params['density'].value
            background_scaling = params['background_scaling'].value

            self.background_spectrum.scaling = background_scaling
            self.calculate_transforms()
            self.optimize_sq(iterations, fcn_callback=callback_fcn)

            r, fr = self.fr_spectrum.limit(0, self.r_cutoff).data

            output = (-fr - 4 * np.pi * convert_density_to_atoms_per_cubic_angstrom(self.composition, density) *
                      r) ** 2

            self.write_output(
                u'{} X: {:.3f} Den: {:.3f}'.format(self.iteration, np.sum(output) / (r[1] - r[0]), density))
            self.iteration += 1
            return output

        minimize(optimization_fcn, params)
        self.write_fit_results(params)

    def write_output(self, msg, output_txt=None):
        if output_txt is None:
            print(msg)
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
        output = '\nFit Results:\n'
        output += '-Background Scaling:\n  % .3g +/- %.3g\n' % (params['background_scaling'].value,
                                                                params['background_scaling'].stderr)
        output += '-Density:\n  % .3g +/- %.3g\n' % (params['density'].value,
                                                     params['density'].stderr)
        self.write_output(output)

    def set_diamond_content(self, content_value):
        if content_value is 0:
            self.diamond_background_spectrum = None
            self.calculate_transforms()
            return

        q, _ = self.background_spectrum.data
        int = calculate_incoherent_scattering({'C': 1}, q) * content_value
        self.diamond_background_spectrum = Pattern(q, int)
        self.calculate_transforms()

    def optimize_diamond_content(self, diamond_content=0, callback_fcn=None):
        params = Parameters()
        if diamond_content == 0:
            diamond_content = 20
        params.add("content", value=diamond_content, min=0)

        def optimization_fcn(params):
            diamond_content = params['content'].value
            self.set_diamond_content(diamond_content)
            low_r_spectrum = self.gr_spectrum.limit(0, self.r_cutoff)
            if callback_fcn is not None:
                callback_fcn(diamond_content)
            return low_r_spectrum.data[1]

        result = minimize(optimization_fcn, params)
        print(result)

# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from .configuration import GlassureConfiguration, ExtrapolationConfiguration, TransformConfiguration, Sample
import numpy as np
import json
from lmfit import Parameters, minimize
from qtpy import QtGui, QtCore

from ...core.pattern import Pattern
from ...core.utility import calculate_incoherent_scattering, convert_density_to_atoms_per_cubic_angstrom
from ...core import calculate_sq, calculate_gr, calculate_fr
from ...core.optimization import optimize_sq
from ...core.soller_correction import SollerCorrectionGui
from ...core.transfer_function import calculate_transfer_function

from ...core.utility import extrapolate_to_zero_linear, extrapolate_to_zero_step, extrapolate_to_zero_spline, \
    extrapolate_to_zero_poly, calculate_s0

from ...core.scattering_factors import get_available_elements


class GlassureModel(QtCore.QObject):
    configurations_changed = QtCore.Signal()
    configuration_selected = QtCore.Signal(int)
    data_changed = QtCore.Signal()
    sq_changed = QtCore.Signal(Pattern)
    fr_changed = QtCore.Signal(Pattern)
    gr_changed = QtCore.Signal(Pattern)

    def __init__(self):
        super(GlassureModel, self).__init__()

        self.configurations = []
        self.configurations.append(GlassureConfiguration())
        self.configuration_ind = 0

        self.auto_update = True
        self.optimization_callback = None

    def load_data(self, filename):
        self.original_pattern.load(filename)
        self.calculate_transforms()

    def load_bkg(self, filename):
        self.current_configuration.background_pattern = Pattern.from_file(filename)
        self.calculate_transforms()

    def reset_bkg(self):
        self.current_configuration.background_pattern = None
        self.calculate_transforms()

    @property
    def current_configuration(self):
        """
        :rtype: GlassureConfiguration
        """
        return self.configurations[self.configuration_ind]

    def add_configuration(self):
        self.configurations.append(self.current_configuration.copy())
        self.configuration_ind = len(self.configurations) - 1
        self.configurations_changed.emit()

    def remove_configuration(self):
        """
        Removes the currently selected configuration, unless only one
        configuration is left
        """
        if len(self.configurations) == 1:
            return

        del self.configurations[self.configuration_ind]

        if self.configuration_ind >= len(self.configurations):
            self.configuration_ind = len(self.configurations) - 1
        self.configurations_changed.emit()

    def select_configuration(self, ind):
        if ind < 0:
            ind = len(self.configurations) + ind
        self.configuration_ind = ind
        self.configuration_selected.emit(ind)

    def to_json(self, filename):
        data = [c.to_dict() for c in self.configurations]
        with open(filename, 'w') as f:
            json.dump(data, f)

    def read_json(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        self.configurations = [GlassureConfiguration.from_dict(d)
                               for d in data]
        self.configuration_ind = 0
        self.configurations_changed.emit()

    @property
    def atomic_density(self):
        if len(self.composition):
            return convert_density_to_atoms_per_cubic_angstrom(self.composition, self.density)
        return 0

    @property
    def original_pattern(self):
        return self.current_configuration.original_pattern

    @original_pattern.setter
    def original_pattern(self, new_pattern):
        self.current_configuration.original_pattern = new_pattern

    @property
    def background_pattern(self):
        if self.current_configuration.diamond_bkg_pattern is None:
            if self.current_configuration.background_pattern is None:
                return None
            else:
                return self.current_configuration.background_pattern
        if self.current_configuration.background_pattern is None:
            return self.current_configuration.diamond_bkg_pattern
        return self.current_configuration.background_pattern + \
            self.current_configuration.diamond_bkg_pattern

    @property
    def diamond_bkg_pattern(self):
        return self.current_configuration.diamond_bkg_pattern

    @diamond_bkg_pattern.setter
    def diamond_bkg_pattern(self, new_pattern):
        self.current_configuration.diamond_bkg_pattern = new_pattern

    @property
    def background_scaling(self):
        return self.current_configuration.background_pattern.scaling

    @background_scaling.setter
    def background_scaling(self, new_value):
        self.current_configuration.background_pattern.scaling = new_value
        self.calculate_transforms()

    @property
    def sq_pattern(self):
        return self.current_configuration.sq_pattern

    @sq_pattern.setter
    def sq_pattern(self, new_sq):
        self.current_configuration.sq_pattern = new_sq
        self.sq_changed.emit(new_sq)

    @property
    def fr_pattern(self):
        return self.current_configuration.fr_pattern

    @fr_pattern.setter
    def fr_pattern(self, new_fr):
        self.current_configuration.fr_pattern = new_fr
        self.fr_changed.emit(new_fr)

    @property
    def gr_pattern(self):
        return self.current_configuration.gr_pattern

    @gr_pattern.setter
    def gr_pattern(self, new_gr):
        self.current_configuration.gr_pattern = new_gr
        self.gr_changed.emit(new_gr)

    @property
    def sample(self):
        return self.current_configuration.sample

    @sample.setter
    def sample(self, new_sample):
        self.current_configuration.sample = new_sample
        self.calculate_transforms()

    def add_element(self):
        elements = get_available_elements(self.sample.sf_source)
        for element in elements:
            if element not in self.sample.composition.keys():
                self.sample.composition[element] = 1
                break
        self.calculate_transforms()

    @property
    def sf_source(self):
        return self.sample.sf_source

    @sf_source.setter
    def sf_source(self, new_source):
        self.sample.sf_source = new_source
        self.calculate_transforms()

    @property
    def composition(self):
        return self.sample.composition

    @composition.setter
    def composition(self, new_composition):
        self.sample.composition = new_composition
        self.calculate_transforms()

    @property
    def density(self):
        return self.sample.density

    @density.setter
    def density(self, new_density):
        self.sample.density = new_density
        self.calculate_transforms()

    @property
    def density_error(self):
        return self.sample.density_error

    @density_error.setter
    def density_error(self, new_density_error):
        self.sample.density_error = new_density_error

    @property
    def transform_config(self) -> TransformConfiguration:
        return self.current_configuration.transform_config

    @transform_config.setter
    def transform_config(self, new_transform_config: TransformConfiguration):
        self.current_configuration.transform_config = new_transform_config
        self.calculate_transforms()

    @property
    def q_min(self):
        return self.transform_config.q_min

    @q_min.setter
    def q_min(self, new_q_min):
        self.transform_config.q_min = new_q_min
        self.calculate_transforms()

    @property
    def q_max(self):
        return self.transform_config.q_max

    @q_max.setter
    def q_max(self, new_q_max):
        self.transform_config.q_max = new_q_max
        self.calculate_transforms()

    @property
    def r_min(self):
        return self.transform_config.r_min

    @r_min.setter
    def r_min(self, new_r_min):
        self.transform_config.r_min = new_r_min
        self.calculate_transforms()

    @property
    def r_max(self):
        return self.transform_config.r_max

    @r_max.setter
    def r_max(self, new_r_max):
        self.transform_config.r_max = new_r_max
        self.calculate_transforms()

    @property
    def r_step(self):
        return self.transform_config.r_step

    @r_step.setter
    def r_step(self, new_r_step):
        self.transform_config.r_step = new_r_step
        self.calculate_transforms()

    @property
    def optimize(self):
        return self.current_configuration.optimize_config.enable

    @optimize.setter
    def optimize(self, new_flag):
        self.current_configuration.optimize_config.enable = new_flag
        self.calculate_transforms()

    @property
    def r_cutoff(self):
        return self.current_configuration.optimize_config.r_cutoff

    @r_cutoff.setter
    def r_cutoff(self, new_r_cutoff):
        self.current_configuration.optimize_config.r_cutoff = new_r_cutoff
        self.calculate_transforms()

    @property
    def optimization_iterations(self):
        return self.current_configuration.optimize_config.iterations

    @optimization_iterations.setter
    def optimization_iterations(self, new_value):
        self.current_configuration.optimize_config.iterations = new_value

    @property
    def optimization_attenuation(self):
        return self.current_configuration.optimize_config.attenuation

    @optimization_attenuation.setter
    def optimization_attenuation(self, new_value):
        self.current_configuration.optimize_config.attenuation = new_value

    @property
    def use_modification_fcn(self):
        return self.transform_config.use_modification_fcn

    @use_modification_fcn.setter
    def use_modification_fcn(self, value):
        self.transform_config.use_modification_fcn = value
        self.calculate_transforms()

    @property
    def sq_method(self):
        return self.transform_config.sq_method

    @sq_method.setter
    def sq_method(self, value):
        self.transform_config.sq_method = value
        self.calculate_transforms()

    @property
    def normalization_method(self):
        return self.transform_config.normalization_method

    @normalization_method.setter
    def normalization_method(self, value):
        self.transform_config.normalization_method = value
        self.calculate_transforms()

    @property
    def extrapolation_config(self) -> ExtrapolationConfiguration:
        return self.current_configuration.extrapolation_config

    @extrapolation_config.setter
    def extrapolation_config(self, value: ExtrapolationConfiguration):
        self.current_configuration.extrapolation_config = value
        self.calculate_transforms()

    @property
    def use_soller_correction(self):
        return self.current_configuration.soller_config.enable

    @use_soller_correction.setter
    def use_soller_correction(self, value):
        self.current_configuration.soller_config.enable = value
        self.calculate_transforms()

    @property
    def soller_correction(self):
        return self.current_configuration.soller_config.correction

    @soller_correction.setter
    def soller_correction(self, new_value):
        self.current_configuration.soller_config.correction = new_value
        self.calculate_transforms()

    @property
    def soller_parameters(self):
        return self.current_configuration.soller_config.parameters

    @soller_parameters.setter
    def soller_parameters(self, new_parameters):
        self.current_configuration.soller_config.parameters = new_parameters
        self.calculate_transforms()

    @property
    def use_transfer_function(self):
        return self.current_configuration.transfer_config.enable

    @use_transfer_function.setter
    def use_transfer_function(self, new_value):
        self.current_configuration.transfer_config.enable = new_value
        if new_value:
            self.update_transfer_function()
        else:
            self.calculate_transforms()

    @property
    def transfer_function(self):
        return self.current_configuration.transfer_config.function

    @property
    def transfer_function_smoothing(self):
        return self.current_configuration.transfer_config.smoothing

    @transfer_function_smoothing.setter
    def transfer_function_smoothing(self, new_value):
        self.current_configuration.transfer_config.smoothing = new_value
        self.update_transfer_function()

    @property
    def transfer_std_pattern(self):
        """
        :rtype: Pattern
        """
        return self.current_configuration.transfer_config.std_pattern

    @transfer_std_pattern.setter
    def transfer_std_pattern(self, new_pattern):
        self.current_configuration.transfer_config.std_pattern = new_pattern

    @property
    def transfer_std_bkg_pattern(self):
        """
        :rtype Pattern:
        """
        return self.current_configuration.transfer_config.std_bkg_pattern

    @transfer_std_bkg_pattern.setter
    def transfer_std_bkg_pattern(self, new_pattern):
        self.current_configuration.transfer_config.std_bkg_pattern = new_pattern
        self.update_transfer_function()

    @property
    def transfer_std_bkg_scaling(self):
        return self.current_configuration.transfer_config.std_bkg_scaling

    @transfer_std_bkg_scaling.setter
    def transfer_std_bkg_scaling(self, new_value):
        self.current_configuration.transfer_config.std_bkg_scaling = new_value
        self.update_transfer_function()

    @property
    def transfer_sample_pattern(self):
        """
        :rtype: Pattern
        """
        return self.current_configuration.transfer_config.sample_pattern

    @transfer_sample_pattern.setter
    def transfer_sample_pattern(self, new_pattern):
        self.current_configuration.transfer_config.sample_pattern = new_pattern

    @property
    def transfer_sample_bkg_pattern(self):
        """
        :rtype Pattern:
        """
        return self.current_configuration.transfer_config.sample_bkg_pattern

    @transfer_sample_bkg_pattern.setter
    def transfer_sample_bkg_pattern(self, new_pattern):
        self.current_configuration.transfer_config.sample_bkg_pattern = new_pattern
        self.update_transfer_function()

    @property
    def transfer_sample_bkg_scaling(self):
        return self.current_configuration.transfer_config.sample_bkg_scaling

    @transfer_sample_bkg_scaling.setter
    def transfer_sample_bkg_scaling(self, new_value):
        self.current_configuration.transfer_config.sample_bkg_scaling = new_value
        self.update_transfer_function()

    def set_smooth(self, value):
        self.original_pattern.set_smoothing(value)
        if self.background_pattern is not None:
            self.current_configuration.background_pattern.set_smoothing(value)
        self.calculate_transforms()

    def update_parameter(self,
                         sample_config: Sample,
                         transform_config: TransformConfiguration,
                         extrapolation_config: ExtrapolationConfiguration,
                         optimize_active,
                         r_cutoff,
                         optimize_iterations,
                         optimize_attenuation):

        self.auto_update = False
        self.sample = sample_config
        validate_composition(self.sample.composition, self.sample.sf_source)

        self.transform_config = transform_config
        self.extrapolation_config = extrapolation_config

        self.optimize = optimize_active
        self.r_cutoff = r_cutoff
        self.optimization_iterations = optimize_iterations
        self.optimization_attenuation = optimize_attenuation

        self.auto_update = True
        self.calculate_transforms()

    def calculate_transforms(self):
        if not self.auto_update:
            return

        if len(self.composition) != 0 and self.original_pattern:
            self.calculate_sq()

            if self.optimize:
                self.sq_pattern = optimize_sq(
                    self.sq_pattern, self.r_cutoff,
                    iterations=self.optimization_iterations,
                    atomic_density=convert_density_to_atoms_per_cubic_angstrom(
                        self.composition,
                        self.density),
                    use_modification_fcn=False,
                    attenuation_factor=self.optimization_attenuation,
                    fcn_callback=self.optimization_callback,
                    fourier_transform_method=self.transform_config.fourier_transform_method)
            self.calculate_fr()
            self.calculate_gr()
        self.data_changed.emit()

    def calculate_sq(self):
        if self.background_pattern is not None:
            sample_pattern = (self.original_pattern - self.background_pattern) \
                .limit(self.q_min, self.q_max)
        else:
            sample_pattern = self.original_pattern.limit(
                self.q_min, self.q_max)

        if self.use_transfer_function and self.transfer_function is not None:
            sample_pattern.y = sample_pattern.y * \
                               self.transfer_function(sample_pattern.x)

        if self.use_soller_correction:
            q, intensity = sample_pattern.data
            if self.soller_correction is None or \
                    self.soller_correction._max_thickness < self.soller_parameters['sample_thickness'] or \
                    self.soller_correction.wavelength != self.soller_parameters['wavelength'] or \
                    self.soller_correction._inner_radius != self.soller_parameters['inner_radius'] or \
                    self.soller_correction._outer_radius != self.soller_parameters['outer_radius'] or \
                    self.soller_correction._inner_width != self.soller_parameters['inner_width'] or \
                    self.soller_correction._outer_width != self.soller_parameters['outer_width'] or \
                    self.soller_correction._inner_length != self.soller_parameters['inner_length'] or \
                    self.soller_correction._outer_length != self.soller_parameters['outer_length']:

                if 2 > self.soller_parameters['sample_thickness']:
                    max_thickness = 2
                else:
                    max_thickness = self.soller_parameters["sample_thickness"] * 1.5

                self.soller_correction = SollerCorrectionGui(
                    q=q,
                    wavelength=self.soller_parameters['wavelength'],
                    max_thickness=max_thickness,
                    inner_radius=self.soller_parameters['inner_radius'],
                    outer_radius=self.soller_parameters['outer_radius'],
                    inner_width=self.soller_parameters['inner_width'],
                    outer_width=self.soller_parameters['outer_width'],
                    inner_length=self.soller_parameters['inner_length'],
                    outer_length=self.soller_parameters['outer_length'])

            sample_pattern = Pattern(
                q, self.soller_correction.transfer_function_sample(
                    self.soller_parameters['sample_thickness']) * intensity)

        self.sq_pattern = calculate_sq(
            sample_pattern,
            density=self.density,
            composition=self.composition,
            normalization_method=self.normalization_method,
            method=self.sq_method,
            sf_source=self.sf_source,
        )
        self.perform_extrapolation()

    def perform_extrapolation(self):
        if not self.extrapolation_config.activate:
            return

        extrapolation_method = self.extrapolation_config.method
        if self.extrapolation_config.s0_auto:
            self.extrapolation_config.s0 = calculate_s0(self.composition, self.sf_source)

        s0 = self.extrapolation_config.s0

        if extrapolation_method == 'step':
            self.sq_pattern = extrapolate_to_zero_step(self.sq_pattern, y0=s0)
        elif extrapolation_method == 'linear':
            self.sq_pattern = extrapolate_to_zero_linear(self.sq_pattern, y0=s0)
        elif extrapolation_method == 'spline':
            self.sq_pattern = extrapolate_to_zero_spline(
                self.sq_pattern,
                self.extrapolation_config.fit_q_max,
                y0=s0,
                replace=self.extrapolation_config.fit_replace)
        elif extrapolation_method == 'poly':
            self.sq_pattern = extrapolate_to_zero_poly(
                self.sq_pattern,
                self.extrapolation_config.fit_q_max,
                y0=s0,
                replace=self.extrapolation_config.fit_replace)

    def calculate_fr(self):
        self.fr_pattern = calculate_fr(
            self.sq_pattern,
            r=np.arange(self.r_min, self.r_max + self.r_step * 0.5, self.r_step),
            method=self.transform_config.fourier_transform_method,
            use_modification_fcn=self.use_modification_fcn)

    def calculate_gr(self):
        self.gr_pattern = calculate_gr(
            self.fr_pattern, self.density, self.composition)


    def optimize_density_and_scaling(self, density_min, density_max, bkg_min, bkg_max, iterations, callback_fcn=None,
                                     output_txt=None):
        params = Parameters()
        params.add("density", value=self.density, min=density_min, max=density_max)
        params.add("background_scaling", value=self.background_scaling, min=bkg_min, max=bkg_max)

        self.iteration = 0

        def optimization_fcn(params):
            density = params['density'].value
            background_scaling = params['background_scaling'].value

            self.background_pattern.scaling = background_scaling
            self.density = density
            self.calculate_transforms()
            # self.optimize_sq(iterations, fcn_callback=callback_fcn)

            r, gr = self.gr_pattern.limit(0, self.r_cutoff * 0.5).data

            output = gr ** 2

            self.write_output(u'{} X^2: {:.3f} Bkg_Scaling: {:.2f} Den: {:.3f}'.format(
                self.iteration, np.sum(output) / len(r), background_scaling, density),
                output_txt
            )
            self.iteration += 1
            return output

        res = minimize(optimization_fcn, params, method='least_squares', xtol=1e-3)
        self.write_fit_results(res.params, output_txt)
        return res.params

    def write_output(self, msg, output_txt=None):
        if output_txt is None:
            print(msg)
        else:
            print(msg)
            previous_txt = str(output_txt.toPlainText())
            new_txt = previous_txt + "\n" + str(msg)
            output_txt.setPlainText(new_txt)
            output_txt.verticalScrollBar().setValue(output_txt.verticalScrollBar().maximum())
            QtCore.QCoreApplication.processEvents()
            output_txt.verticalScrollBar().setValue(output_txt.verticalScrollBar().maximum())
            QtCore.QCoreApplication.processEvents()

    def write_fit_results(self, params, output_txt=None):
        output = '\nFit Results:\n'
        if params['density'].stderr is None:
            params['density'].stderr = np.nan
        if params['background_scaling'].stderr is None:
            params['background_scaling'].stderr = np.nan
        output += '-Background Scaling:\n  % .3g +/- %.3g\n' % ( \
            params['background_scaling'].value, params['background_scaling'].stderr)
        output += '-Density:\n  % .3g +/- %.3g\n' % (params['density'].value, params['density'].stderr)
        self.write_output(output, output_txt)

    def set_diamond_content(self, content_value):
        if content_value == 0:
            self.diamond_bkg_pattern = None
            self.calculate_transforms()
            return

        q, _ = self.background_pattern.data
        int = calculate_incoherent_scattering({'C': 1}, q) * content_value
        self.diamond_bkg_pattern = Pattern(q, int)
        self.calculate_transforms()

    def optimize_diamond_content(self, diamond_content=0, callback_fcn=None):
        params = Parameters()
        if diamond_content == 0:
            diamond_content = 20
        params.add("content", value=diamond_content, min=0)

        def optimization_fcn(params):
            diamond_content = params['content'].value
            self.set_diamond_content(diamond_content)
            low_r_pattern = self.gr_pattern.limit(0, self.r_cutoff)
            if callback_fcn is not None:
                callback_fcn(diamond_content)
            return low_r_pattern.data[1]

        result = minimize(optimization_fcn, params)
        print(result)

    def update_transfer_function(self):
        if self.transfer_std_pattern is None or \
                self.transfer_sample_pattern is None or \
                not self.use_transfer_function:
            return
        q_min = np.max([self.transfer_std_pattern.x[0], self.transfer_sample_pattern.x[0]])
        q_max = np.min([self.transfer_std_pattern.x[-1], self.transfer_sample_pattern.x[-1]])

        if self.transfer_std_bkg_pattern is None:
            std_pattern = self.transfer_std_pattern
        else:
            std_pattern = self.transfer_std_pattern - self.transfer_std_bkg_scaling * self.transfer_std_bkg_pattern

        if self.transfer_sample_bkg_pattern is None:
            sample_pattern = self.transfer_sample_pattern
        else:
            sample_pattern = self.transfer_sample_pattern - \
                             self.transfer_sample_bkg_scaling * \
                             self.transfer_sample_bkg_pattern

        self.current_configuration.transfer_config.function = \
            calculate_transfer_function(
                std_pattern.limit(q_min, q_max),
                sample_pattern.limit(q_min, q_max),
                smooth_factor=self.transfer_function_smoothing
            )
        self.calculate_transforms()

    def load_transfer_std_pattern(self, filename):
        self.transfer_std_pattern = Pattern.from_file(filename)

    def load_transfer_std_bkg_pattern(self, filename):
        self.transfer_std_bkg_pattern = Pattern.from_file(filename)

    def load_transfer_sample_pattern(self, filename):
        self.transfer_sample_pattern = Pattern.from_file(filename)

    def load_transfer_sample_bkg_pattern(self, filename):
        self.transfer_sample_bkg_pattern = Pattern.from_file(filename)


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, (np.floating, np.complexfloating)):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.string_):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super(NpEncoder, self).default(obj)


def validate_composition(composition: dict[str, float], sf_source: str):
    for element in list(composition.keys()):
        if element not in get_available_elements(sf_source):
            del composition[element]

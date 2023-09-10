# -*- coding: utf-8 -*-
import numpy as np
from .utility import set_widget_text, click_checkbox, click_button, prepare_file_loading, data_path
from glassure.gui.widgets.control.density_optimization import DensityOptimizationWidget
from glassure.gui.widgets.glassure_widget import GlassureWidget

from glassure.gui.controller.glassure_controller import GlassureController
from glassure.gui.model.glassure_model import GlassureModel


def test_density_optimization(main_controller: GlassureController,
                              density_optimization_widget: DensityOptimizationWidget,
                              model: GlassureModel):
    model.load_data(data_path('Mg2SiO4_ambient.xy'))
    model.load_bkg(data_path('Mg2SiO4_ambient_bkg.xy'))
    model.composition = {'Mg': 2, 'Si': 1, 'O': 4}
    model.r_min = 0
    model.q_max = 17
    model.optimize = True
    model.current_configuration.optimize_config.r_cutoff = 0.8

    density_optimization_widget.density_min_txt.setText('2.0')
    density_optimization_widget.density_max_txt.setText('5.0')
    density_optimization_widget.bkg_min_txt.setText('0.8')
    density_optimization_widget.bkg_max_txt.setText('1.3')

    density_result = []
    density_result_err = []
    r_cutoffs = np.arange(0.4, 1.6, 0.05)
    for r_cutoff in r_cutoffs:
        model.current_configuration.optimize_config.r_cutoff = r_cutoff
        params = model.optimize_density_and_scaling(1.2, 5.0, 0.8, 1.3, 5)

        density_result.append(params['density'].value)
        density_result_err.append(params['density'].stderr)

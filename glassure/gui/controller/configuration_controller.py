
from ..widgets.glassure_widget import GlassureWidget
from ..model.glassure_model import GlassureModel


class ConfigurationController(object):
    def __init__(self, main_widget, glassure_model):
        """
        :param main_widget:
        :type main_widget: GlassureWidget
        :param glassure_model:
        :type glassure_model: GlassureModel
        """

        self.main_widget = main_widget
        self.model = glassure_model

        self.connect_signals()


        self.update_configurations_tw()

    def connect_signals(self):
        self.main_widget.freeze_configuration_btn.clicked.connect(self.model.add_configuration)
        self.main_widget.remove_configuration_btn.clicked.connect(self.model.remove_configuration)
        self.main_widget.configuration_tw.currentCellChanged.connect(self.model.select_configuration)

        self.model.configurations_changed.connect(self.update_configurations_tw)
        self.model.configuration_selected.connect(self.configuration_selected)

    def freeze_configuration(self):
        self.model.add_configuration()

    def remove_configuration(self):
        self.main_widget.configuration_widget.remove_configuration()

    def update_configurations_tw(self):
        self.main_widget.configuration_tw.setRowCount(0)
        for configuration in self.model.configurations:
            color = configuration.color
            self.main_widget.configuration_widget.add_configuration(
                configuration.name,
                '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2]))
            )
        self.main_widget.configuration_tw.selectRow(self.model.configuration_ind)

    def configuration_selected(self, ind):
        # filenames
        self.main_widget.data_filename_lbl.setText(self.model.original_pattern.name)
        self.main_widget.bkg_filename_lbl.setText(self.model.current_configuration.background_pattern.name)

        # background scaling and smoothing
        self.main_widget.bkg_scaling_sb.setValue(self.model.current_configuration.background_pattern.scaling)
        self.main_widget.smooth_sb.setValue(self.model.original_pattern.smoothing)

        # composition widget
        self.main_widget.set_composition(self.model.composition)
        self.main_widget.density_txt.setText(str(self.model.density))

        # parameters widget
        self.main_widget.q_min_txt.setText(str(self.model.q_min))
        self.main_widget.q_max_txt.setText(str(self.model.q_max))

        self.main_widget.r_min_txt.setText(str(self.model.r_min))
        self.main_widget.r_max_txt.setText(str(self.model.r_max))

        self.main_widget.use_modification_cb.setChecked(self.model.use_modification_fcn)
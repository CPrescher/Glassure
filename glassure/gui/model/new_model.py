from qtpy import QtCore
from .new_config import GuiConfiguration
from ...core.pattern import Pattern
from ...core.configuration import (
    SampleConfig,
    Input,
    Result,
    TransformConfig,
    ExtrapolationConfig,
    OptimizeConfig,
    FitNormalization,
    IntNormalization,
)
from ...core.calc import process_input


class GlassureModel(QtCore.QObject):
    configuration_changed = QtCore.Signal()
    configuration_selected = QtCore.Signal()
    input_changed = QtCore.Signal()
    result_changed = QtCore.Signal()

    def __init__(self):
        super(GlassureModel, self).__init__()

        self.configurations = []
        self.configurations.append(GuiConfiguration())
        self.configuration_ind = 0

        self.input_changed.connect(self.process)
        self.configuration_selected.connect(self.process)

    @property
    def current_configuration(self) -> GuiConfiguration:
        return self.configurations[self.configuration_ind]

    @property
    def input(self) -> Input:
        return self.current_configuration.input

    @property
    def result(self) -> Result:
        return self.current_configuration.result

    def add_configuration(self):
        self.configurations.append(GuiConfiguration())
        self.configuration_changed.emit()
        self.select_configuration(len(self.configurations) - 1)

    def select_configuration(self, ind: int):
        self.configuration_ind = ind
        self.configuration_selected.emit()

    def remove_configuration(self, ind: int):
        if len(self.configurations) == 1:
            return
        self.configurations.pop(ind)
        self.configuration_changed.emit()
        self.select_configuration(min(ind, len(self.configurations) - 1))

    def update_input(self, input: Input):
        self.current_configuration.input = input
        self.input_changed.emit()

    def update_sample(self, sample_config: SampleConfig):
        self.input.config.sample = sample_config
        self.input_changed.emit()

    def update_transform(self, transform_config: TransformConfig):
        self.input.config.transform = transform_config
        self.input_changed.emit()

    def update_normalization(
        self, normalization_config: FitNormalization | IntNormalization
    ):
        self.input.config.transform.normalization = normalization_config
        self.input_changed.emit()

    def update_extrapolation(self, extrapolation_config: ExtrapolationConfig):
        self.input.config.transform.extrapolation = extrapolation_config
        self.input_changed.emit()

    def update_optimize(self, optimize_config: OptimizeConfig | None):
        self.input.config.optimize = optimize_config
        self.input_changed.emit()

    def process(self):
        """
        Process the current input configuration and update the result.
        """
        try:
            result = process_input(self.input)
            self.current_configuration.result = result
            self.result_changed.emit()
        except ValueError as e:
            print("Could not process input:", e)

    def load_data(self, path: str):
        """
        Load data from file and update the input configuration.
        """
        self.input.data = Pattern.from_file(path)
        self.input_changed.emit()

    def load_bkg(self, path: str):
        """
        Load background from file and update the input configuration.
        """
        self.input.bkg = Pattern.from_file(path)
        self.input_changed.emit()

    @property
    def bkg_scaling(self):
        return self.input.bkg_scaling

    @bkg_scaling.setter
    def bkg_scaling(self, value: float):
        self.input.bkg_scaling = value
        self.input_changed.emit()

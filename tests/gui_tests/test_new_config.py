import numpy as np
from glassure.gui.model.new_config import GuiConfiguration


def test_new_config_empty():
    config = GuiConfiguration()
    assert config.input.config.sample.composition == {}
    assert config.input.data is None
    assert config.name == "Config: 1"

    config2 = GuiConfiguration()
    assert config2.name == "Config: 2"
    assert not np.array_equal(config.color, config2.color)

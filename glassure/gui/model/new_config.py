from colorsys import hsv_to_rgb

import numpy as np
from ...core.configuration import Input, Result


class GuiConfiguration(object):
    num = 0

    def __init__(self):
        GuiConfiguration.num += 1
        self.input = Input()
        self.result = Result(input=self.input)

        self.name = "Config: {}".format(GuiConfiguration.num)
        self.color = calculate_color(GuiConfiguration.num)


def calculate_color(ind):
    s = 0.8
    v = 0.8
    h = (0.19 * (ind + 2)) % 1
    return np.array(hsv_to_rgb(h, s, v)) * 255

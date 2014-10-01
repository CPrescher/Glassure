# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from .Spectrum import Spectrum
from .HelperModule import Observable

class GlassureModel(Observable):

    def __init__(self):
        super(GlassureModel, self).__init__()
        self.original_spectrum = Spectrum()
        self.background_spectrum = Spectrum()

    def load_data(self, filename):
        self.original_spectrum.load(filename)
        self.notify()

    def load_bkg(self, filename):
        self.background_spectrum.load(filename)
        self.original_spectrum.set_background(self.background_spectrum)
        self.notify()

    def set_bkg_scale(self, scaling):
        self.background_spectrum.scaling = scaling
        self.notify()

    def set_bkg_offset(self, offset):
        self.background_spectrum.offset = offset
        self.notify()

    def set_smooth(self, value):
        self.original_spectrum.set_smoothing(value)
        self.notify()
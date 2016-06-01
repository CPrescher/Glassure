# -*- coding: utf8 -*-

from ..qt import QtGui

from ..widgets.glassure import GlassureWidget
from ..model.glassure import GlassureModel


class SollerController(object):
    def __init__(self, widget, glassure_model):
        """
        :param widget:
        :type widget: GlassureWidget
        :param glassure_model:
        :type glassure_model: GlassureModel
        """

        self.widget = widget
        self.soller_widget = widget.soller_widget
        self.model = glassure_model

        self.connect_signals()

    def connect_signals(self):
        self.soller_widget.soller_parameters_changed.connect(self.soller_parameters_changed)

    def soller_parameters_changed(self):
        print("haha")
        self.model.soller_parameters = self.soller_widget.get_parameters()

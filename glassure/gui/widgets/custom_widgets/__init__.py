# -*- coding: utf8 -*-

from ...qt import QtGui
from .box import ExpandableBox
from .lines import HorizontalLine
from .spectrum_widget import SpectrumWidget


def VerticalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

def HorizontalSpacerItem():
    return QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
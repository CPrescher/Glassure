# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PySide import QtGui

def HorizontalLine():
    frame = QtGui.QFrame()
    frame.setFrameShape(QtGui.QFrame.HLine)
    frame.setStyleSheet("border: 2px solid #CCC;")
    frame.setFrameShadow(QtGui.QFrame.Sunken)
    return frame
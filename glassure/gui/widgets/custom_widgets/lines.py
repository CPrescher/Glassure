# -*- coding: utf8 -*-

from PySide import QtGui


def HorizontalLine():
    frame = QtGui.QFrame()
    frame.setFrameShape(QtGui.QFrame.HLine)
    frame.setStyleSheet("border: 2px solid #CCC;")
    frame.setFrameShadow(QtGui.QFrame.Sunken)
    return frame

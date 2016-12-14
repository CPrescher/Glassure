# -*- coding: utf8 -*-

from ...qt import QtWidgets


def HorizontalLine():
    frame = QtWidgets.QFrame()
    frame.setFrameShape(QtWidgets.QFrame.HLine)
    frame.setStyleSheet("border: 2px solid #CCC;")
    frame.setFrameShadow(QtWidgets.QFrame.Sunken)
    return frame

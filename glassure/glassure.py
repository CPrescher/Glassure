# -*- coding: utf8 -*-
from __future__ import absolute_import
__author__ = 'Clemens Prescher'

import sys
from PyQt4 import QtGui

from gui.controller.gui_controller import MainController

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    from sys import platform as _platform

    if _platform == "linux" or _platform == "linux2":
        app.setStyle('plastique')
    elif _platform == "win32" or _platform == 'cygwin':
        app.setStyle('plastique')
        # possible values:
        # "windows", "motif", "cde", "plastique", "windowsxp", or "macintosh"
    controller = MainController()
    controller.load_data('tests/data/Mg2SiO4_ambient.xy')
    controller.load_bkg('tests/data/Mg2SiO4_ambient_bkg.xy')
    controller.show_window()
    app.exec_()
    del app
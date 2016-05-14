# -*- coding: utf8 -*-

from __future__ import absolute_import

import sys
from PySide import QtGui

from gui.controller.gui_controller import MainController

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    from sys import platform as _platform

    if _platform != "Darwin":
        app.setStyle('plastique')
        # other possible values: "windows", "motif", "cde", "plastique", "windowsxp", or "macintosh"
    controller = MainController()
    controller.load_data('tests/data/Mg2SiO4_ambient.xy')
    controller.load_bkg('tests/data/Mg2SiO4_ambient_bkg.xy')
    controller.show_window()
    app.exec_()
    del app

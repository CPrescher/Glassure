# -*- coding: utf8 -*-

from __future__ import absolute_import

import sys

from core import __version__ as version
from core._version import get_versions
from gui.controller.glassure import GlassureController
from gui.qt import QtGui
__version__ = get_versions()['version']
del get_versions

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    from sys import platform as _platform

    print("Glassure {}".format(version))

    if _platform != "Darwin":
        app.setStyle('plastique')
        # other possible values: "windows", "motif", "cde", "plastique", "windowsxp", or "macintosh"
    controller = GlassureController()
    controller.load_data('tests/data/Mg2SiO4_ambient.xy')
    controller.load_bkg('tests/data/Mg2SiO4_ambient_bkg.xy')
    controller.show_window()
    app.exec_()
    del app

# -*- coding: utf8 -*-

from __future__ import absolute_import

import sys

from glassure.core import __version__ as version
from glassure.core._version import get_versions
from glassure.gui.controller.glassure import GlassureController
from glassure.gui.qt import QtGui

__version__ = get_versions()['version']
del get_versions


def main():
    app = QtGui.QApplication(sys.argv)
    from sys import platform as _platform

    print("Glassure {}".format(version))

    if _platform != "Darwin":
        app.setStyle('plastique')
    controller = GlassureController()
    controller.show_window()
    app.exec_()
    del app


if __name__ == '__main__':
    main()
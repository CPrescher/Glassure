# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys

from glassure import __version__
from glassure.gui.controller.glassure_controller import GlassureController
from qtpy import QtWidgets


def my_exception_hook(exctype, value, traceback):
    # Print the error and traceback
    print(exctype, value, traceback)


# sys.excepthook = my_exception_hook


def main():
    app = QtWidgets.QApplication(sys.argv)
    from sys import platform as _platform

    print("Glassure {}".format(__version__)) 

    if _platform != "Darwin":
        app.setStyle('plastique')
    controller = GlassureController()
    controller.show_window()
    app.exec_()
    del app


if __name__ == '__main__':
    main()

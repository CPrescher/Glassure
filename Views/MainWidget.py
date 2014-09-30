# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtGui

from UiFiles.MainUI import Ui_MainWidget

class MainWidget(QtGui.QWidget,Ui_MainWidget):

    def __init__(self):
        super(MainWidget, self).__init__(None)
        self.setupUi(self)
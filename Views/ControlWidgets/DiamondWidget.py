# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'


from PyQt4 import QtCore, QtGui

class DiamondWidget(QtGui.QWidget):

    def __init__(self, *args):
        super(DiamondWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()

    def create_widgets(self):
        self.diamond_optimize_btn = QtGui.QPushButton("Optimize")
        self.diamond_lbl = QtGui.QLabel('Amount:')
        self.diamond_txt = QtGui.QLineEdit('0')

    def style_widgets(self):
        self.diamond_optimize_btn.setFlat(True)
        self.diamond_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.diamond_txt.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.diamond_txt.setValidator(QtGui.QDoubleValidator())
        self.diamond_txt.setMaximumWidth(60)

    def create_layout(self):
        self._layout = QtGui.QHBoxLayout()
        self._layout.addWidget(self.diamond_lbl)
        self._layout.addWidget(self.diamond_txt)
        self._layout.addWidget(self.diamond_optimize_btn)

        self.setLayout(self._layout)

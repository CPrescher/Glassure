# -*- coding: utf-8 -*-

from qtpy import QtCore, QtWidgets, QtGui


class DiamondWidget(QtWidgets.QWidget):
    def __init__(self, *args):
        super(DiamondWidget, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()

    def create_widgets(self):
        self.diamond_optimize_btn = QtWidgets.QPushButton("Optimize")
        self.diamond_lbl = QtWidgets.QLabel('Amount:')
        self.diamond_txt = QtWidgets.QLineEdit('0')

    def style_widgets(self):
        self.diamond_optimize_btn.setFlat(True)
        self.diamond_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.diamond_txt.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.diamond_txt.setValidator(QtGui.QDoubleValidator())
        self.diamond_txt.setMaximumWidth(60)

    def create_layout(self):
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.addWidget(self.diamond_lbl)
        self._layout.addWidget(self.diamond_txt)
        self._layout.addWidget(self.diamond_optimize_btn)

        self.setLayout(self._layout)

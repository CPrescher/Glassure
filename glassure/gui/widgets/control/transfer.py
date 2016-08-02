# -*- coding: utf8 -*-

from ...qt import QtGui, QtCore

from ..custom import FlatButton, HorizontalLine, LabelAlignRight


class TransferFunctionWidget(QtGui.QWidget):

    def __init__(self, *args):
        super(TransferFunctionWidget, self).__init__(*args)

        self.create_widgets()
        self.create_layout()
        self.style_widgets()
        self.create_signals()

    def create_widgets(self):
        self.load_std_btn = FlatButton("Load Std")
        self.load_std_bkg_btn = FlatButton("Load Std Bkg")
        self.load_sample_btn = FlatButton("Load Sample")
        self.load_sample_bkg_btn = FlatButton("Load Sample Bkg")

        self.std_filename_lbl = LabelAlignRight('')
        self.std_bkg_filename_lbl = LabelAlignRight("")
        self.sample_filename_lbl = LabelAlignRight("")
        self.sample_bkg_filename_lbl = LabelAlignRight("")

        self.std_bkg_scaling_sb = QtGui.QDoubleSpinBox()
        self.std_bkg_scaling_sb.setValue(1.0)
        self.std_bkg_scaling_sb.setSingleStep(0.01)

        self.sample_bkg_scaling_sb = QtGui.QDoubleSpinBox()
        self.sample_bkg_scaling_sb.setValue(1.0)
        self.sample_bkg_scaling_sb.setSingleStep(0.01)

        self.smooth_sb = QtGui.QDoubleSpinBox()
        self.smooth_sb.setValue(1.0)
        self.smooth_sb.setSingleStep(0.1)

    def create_layout(self):
        self.main_layout = QtGui.QVBoxLayout()

        self.activate_cb = QtGui.QCheckBox("activate")
        self.main_layout.addWidget(self.activate_cb)
        self.main_layout.addWidget(HorizontalLine())

        self.transfer_layout = QtGui.QGridLayout()
        self.transfer_layout.addWidget(self.load_sample_btn, 0, 0)
        self.transfer_layout.addWidget(self.sample_filename_lbl, 0, 1)
        self.transfer_layout.addWidget(self.load_sample_bkg_btn, 1, 0)
        self.transfer_layout.addWidget(self.sample_bkg_filename_lbl, 1, 1)

        self.transfer_layout.addWidget(self.load_std_btn, 2, 0)
        self.transfer_layout.addWidget(self.std_filename_lbl, 2, 1)
        self.transfer_layout.addWidget(self.load_std_bkg_btn, 3, 0)
        self.transfer_layout.addWidget(self.std_bkg_filename_lbl, 3, 1)

        self.scaling_gb = QtGui.QGroupBox("")
        self.scaling_layout = QtGui.QGridLayout()
        self.scaling_layout.addItem(QtGui.QSpacerItem(0, 0, QtGui.QSizePolicy.MinimumExpanding,
                                                             QtGui.QSizePolicy.Fixed), 0, 0)
        self.scaling_layout.addWidget(LabelAlignRight("Sample bkg scaling:"), 0, 1)
        self.scaling_layout.addWidget(self.sample_bkg_scaling_sb, 0, 2)
        self.scaling_layout.addWidget(LabelAlignRight("Std bkg scaling:"), 1, 1)
        self.scaling_layout.addWidget(self.std_bkg_scaling_sb, 1, 2)
        self.scaling_layout.addWidget(LabelAlignRight("Smoothing:"), 2, 1)
        self.scaling_layout.addWidget(self.smooth_sb, 2, 2)

        self.scaling_gb.setLayout(self.scaling_layout)
        self.transfer_layout.addWidget(self.scaling_gb, 4, 0, 1, 2)

        self.main_layout.addLayout(self.transfer_layout)
        self.setLayout(self.main_layout)

    def style_widgets(self):
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)

        self.transfer_layout.setContentsMargins(5, 5, 5, 5)

        self.sample_bkg_scaling_sb.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.std_bkg_scaling_sb.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.smooth_sb.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.sample_bkg_scaling_sb.setMinimumWidth(75)
        self.std_bkg_scaling_sb.setMinimumWidth(75)
        self.smooth_sb.setMinimumWidth(75)

    def create_signals(self):
        pass
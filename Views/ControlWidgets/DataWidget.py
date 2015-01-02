# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'


from PyQt4 import QtCore, QtGui

class DataWidget(QtGui.QWidget):
    def __init__(self):
        super(DataWidget, self).__init__()

        self.file_widget = FileWidget()
        self.background_options_gb = BackgroundOptionsGroupBox()
        self.smooth_gb = SmoothGroupBox()

        self._layout = QtGui.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.file_widget)
        self._layout.addWidget(self.background_options_gb)
        self._layout.addWidget(self.smooth_gb)
        self._layout.addSpacing(5)
        self.setLayout(self._layout)


class FileWidget(QtGui.QWidget):
    def __init__(self, *args, **kwargs):
        super(FileWidget, self).__init__(*args, **kwargs)

        self.vertical_layout = QtGui.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)

        self.load_data_btn = QtGui.QPushButton("Load Data")
        self.data_filename_lbl = QtGui.QLabel("None")
        self.data_filename_lbl.setAlignment(QtCore.Qt.AlignRight)
        self.load_background_btn = QtGui.QPushButton("Load Bkg")
        self.background_filename_lbl = QtGui.QLabel("None")
        self.background_filename_lbl.setAlignment(QtCore.Qt.AlignRight)

        self.vertical_layout.addWidget(self.load_data_btn)
        self.vertical_layout.addWidget(self.data_filename_lbl)
        self.vertical_layout.addWidget(self.load_background_btn)
        self.vertical_layout.addWidget(self.background_filename_lbl)

        self.setLayout(self.vertical_layout)


class BackgroundOptionsGroupBox(QtGui.QGroupBox):
    def __init__(self, *args):
        super(BackgroundOptionsGroupBox, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.scale_lbl = QtGui.QLabel("Scale:")
        self.offset_lbl = QtGui.QLabel("Offset:")

        self.scale_sb = QtGui.QDoubleSpinBox()
        self.offset_sb = QtGui.QDoubleSpinBox()

        self.scale_step_txt = QtGui.QLineEdit("0.01")
        self.offset_step_txt = QtGui.QLineEdit("10")

    def style_widgets(self):
        self.scale_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.offset_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.scale_sb.setValue(1.0)
        self.scale_sb.setSingleStep(0.01)
        self.scale_sb.setDecimals(5)

        self.offset_sb.setSingleStep(10)
        self.offset_sb.setRange(-99999999, 9999999)

        self.scale_step_txt.setMaximumWidth(60)
        self.offset_step_txt.setMaximumWidth(60)

        self.scale_sb.setAlignment(QtCore.Qt.AlignRight)
        self.offset_sb.setAlignment(QtCore.Qt.AlignRight)

        self.scale_step_txt.setAlignment(QtCore.Qt.AlignRight)
        self.offset_step_txt.setAlignment(QtCore.Qt.AlignRight)

        self.scale_step_txt.setValidator(QtGui.QDoubleValidator())
        self.offset_step_txt.setValidator(QtGui.QDoubleValidator())

    def create_layout(self):
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(3, 5, 5, 3)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.scale_lbl, 0, 0)
        self.grid_layout.addWidget(self.scale_sb, 0, 1)
        self.grid_layout.addWidget(self.scale_step_txt, 0, 2)

        self.grid_layout.addWidget(self.offset_lbl, 1, 0)
        self.grid_layout.addWidget(self.offset_sb, 1, 1)
        self.grid_layout.addWidget(self.offset_step_txt, 1, 2)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.scale_step_txt.editingFinished.connect(self.scale_step_changed)
        self.offset_step_txt.editingFinished.connect(self.offset_step_changed)

    def scale_step_changed(self):
        self.scale_sb.setSingleStep(float(str(self.scale_step_txt.text())))

    def offset_step_changed(self):
        self.offset_sb.setSingleStep(float(str(self.offset_step_txt.text())))


class SmoothGroupBox(QtGui.QGroupBox):
    def __init__(self, *args):
        super(SmoothGroupBox, self).__init__(*args)
        self.grid_layout = QtGui.QGridLayout()
        self.grid_layout.setContentsMargins(3, 5, 5, 3)
        self.grid_layout.setSpacing(5)

        self.smooth_lbl = QtGui.QLabel("Smooth:")
        self.smooth_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.smooth_sb = QtGui.QDoubleSpinBox()
        self.smooth_sb.setAlignment(QtCore.Qt.AlignRight)
        self.smooth_sb.setSingleStep(1)

        self.smooth_step_txt = QtGui.QLineEdit("1")
        self.smooth_step_txt.setAlignment(QtCore.Qt.AlignRight)
        self.smooth_step_txt.setValidator(QtGui.QDoubleValidator())
        self.smooth_step_txt.setMaximumWidth(60)

        self.smooth_step_txt.editingFinished.connect(self.step_changed)

        self.grid_layout.addWidget(self.smooth_lbl, 0, 0)
        self.grid_layout.addWidget(self.smooth_sb, 0, 1)
        self.grid_layout.addWidget(self.smooth_step_txt, 0, 2)

        self.setLayout(self.grid_layout)

    def step_changed(self):
        self.smooth_sb.setSingleStep(float(str(self.smooth_step_txt.text())))
# -*- coding: utf-8 -*-

from qtpy import QtCore, QtGui, QtWidgets


class DataWidget(QtWidgets.QWidget):
    def __init__(self):
        super(DataWidget, self).__init__()

        self.file_widget = FileWidget()
        self.background_options_gb = BackgroundOptionsGroupBox()
        self.smooth_gb = SmoothGroupBox()

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.file_widget)
        self._layout.addWidget(self.background_options_gb)
        self._layout.addWidget(self.smooth_gb)
        self._layout.addSpacing(5)
        self.setLayout(self._layout)


class FileWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(FileWidget, self).__init__(*args, **kwargs)

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.vertical_layout.setContentsMargins(0, 0, 0, 0)

        self.load_data_btn = QtWidgets.QPushButton("Load Data")
        self.data_filename_lbl = QtWidgets.QLabel("None")
        self.data_filename_lbl.setAlignment(QtCore.Qt.AlignRight)

        self.load_background_btn = QtWidgets.QPushButton("Load Bkg")
        # use icon for reset button
        pixmapi = getattr(QtWidgets.QStyle, "SP_DialogCancelButton")
        icon = self.style().standardIcon(pixmapi)
        self.reset_background_btn = QtWidgets.QPushButton(icon, "")

        self.background_filename_lbl = QtWidgets.QLabel("None")
        self.background_filename_lbl.setAlignment(QtCore.Qt.AlignRight)

        self.vertical_layout.addWidget(self.load_data_btn)
        self.vertical_layout.addWidget(self.data_filename_lbl)

        self.background_btn_layout = QtWidgets.QHBoxLayout()

        self.background_btn_layout.addWidget(self.load_background_btn)
        self.background_btn_layout.addWidget(self.reset_background_btn)

        self.vertical_layout.addLayout(self.background_btn_layout)
        self.vertical_layout.addWidget(self.background_filename_lbl)

        self.setLayout(self.vertical_layout)
        self.style_widgets()

    def style_widgets(self):
        self.reset_background_btn.setMaximumWidth(20)
        self.reset_background_btn.setMaximumHeight(20)
        self.reset_background_btn.setToolTip("Reset Background")


class BackgroundOptionsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, *args):
        super(BackgroundOptionsGroupBox, self).__init__(*args)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()

    def create_widgets(self):
        self.scale_lbl = QtWidgets.QLabel("Scale:")
        self.scale_sb = QtWidgets.QDoubleSpinBox()
        self.scale_step_txt = QtWidgets.QLineEdit("0.01")

    def style_widgets(self):
        self.scale_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.scale_sb.setValue(1.0)
        self.scale_sb.setSingleStep(0.01)
        self.scale_sb.setDecimals(4)
        self.scale_sb.setMinimumWidth(80)

        self.scale_step_txt.setMaximumWidth(60)
        self.scale_sb.setAlignment(QtCore.Qt.AlignRight)
        self.scale_step_txt.setAlignment(QtCore.Qt.AlignRight)
        self.scale_step_txt.setValidator(QtGui.QDoubleValidator())

    def create_layout(self):
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setContentsMargins(3, 5, 5, 3)
        self.grid_layout.setSpacing(5)

        self.grid_layout.addWidget(self.scale_lbl, 0, 0)
        self.grid_layout.addWidget(self.scale_sb, 0, 1)
        self.grid_layout.addWidget(self.scale_step_txt, 0, 2)

        self.setLayout(self.grid_layout)

    def create_signals(self):
        self.scale_step_txt.editingFinished.connect(self.scale_step_changed)

    def scale_step_changed(self):
        self.scale_sb.setSingleStep(float(str(self.scale_step_txt.text())))


class SmoothGroupBox(QtWidgets.QGroupBox):
    def __init__(self, *args):
        super(SmoothGroupBox, self).__init__(*args)
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setContentsMargins(3, 5, 5, 3)
        self.grid_layout.setSpacing(5)

        self.smooth_lbl = QtWidgets.QLabel("Smooth:")
        self.smooth_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.smooth_sb = QtWidgets.QDoubleSpinBox()
        self.smooth_sb.setAlignment(QtCore.Qt.AlignRight)
        self.smooth_sb.setSingleStep(1)
        self.smooth_sb.setMinimumWidth(80)

        self.smooth_step_txt = QtWidgets.QLineEdit("1")
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

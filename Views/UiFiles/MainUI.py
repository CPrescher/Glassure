# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Main.ui'
#
# Created: Tue Sep 30 15:59:50 2014
#      by: PyQt4 UI code generator 4.11.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWidget(object):
    def setupUi(self, MainWidget):
        MainWidget.setObjectName(_fromUtf8("MainWidget"))
        MainWidget.resize(729, 360)
        self.horizontalLayout = QtGui.QHBoxLayout(MainWidget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.spectrum_pg_layout = GraphicsLayoutWidget(MainWidget)
        self.spectrum_pg_layout.setObjectName(_fromUtf8("spectrum_pg_layout"))
        self.horizontalLayout.addWidget(self.spectrum_pg_layout)
        self.widget = QtGui.QWidget(MainWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QtCore.QSize(210, 0))
        self.widget.setMaximumSize(QtCore.QSize(210, 16777215))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.widget)
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setMargin(5)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.load_data_btn = QtGui.QPushButton(self.widget)
        self.load_data_btn.setObjectName(_fromUtf8("load_data_btn"))
        self.verticalLayout.addWidget(self.load_data_btn)
        self.load_bkg_btn = QtGui.QPushButton(self.widget)
        self.load_bkg_btn.setObjectName(_fromUtf8("load_bkg_btn"))
        self.verticalLayout.addWidget(self.load_bkg_btn)
        self.groupBox = QtGui.QGroupBox(self.widget)
        self.groupBox.setTitle(_fromUtf8(""))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setMargin(5)
        self.gridLayout.setSpacing(5)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.offset_step_txt = QtGui.QLineEdit(self.groupBox)
        self.offset_step_txt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.offset_step_txt.setObjectName(_fromUtf8("offset_step_txt"))
        self.gridLayout.addWidget(self.offset_step_txt, 2, 2, 1, 1)
        self.offset_scale_sb = QtGui.QDoubleSpinBox(self.groupBox)
        self.offset_scale_sb.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.offset_scale_sb.setObjectName(_fromUtf8("offset_scale_sb"))
        self.gridLayout.addWidget(self.offset_scale_sb, 2, 1, 1, 1)
        self.bkg_scale_sb = QtGui.QDoubleSpinBox(self.groupBox)
        self.bkg_scale_sb.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.bkg_scale_sb.setObjectName(_fromUtf8("bkg_scale_sb"))
        self.gridLayout.addWidget(self.bkg_scale_sb, 1, 1, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.scale_step_txt = QtGui.QLineEdit(self.groupBox)
        self.scale_step_txt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.scale_step_txt.setObjectName(_fromUtf8("scale_step_txt"))
        self.gridLayout.addWidget(self.scale_step_txt, 1, 2, 1, 1)
        self.gridLayout.setColumnStretch(1, 8)
        self.gridLayout.setColumnStretch(2, 3)
        self.verticalLayout.addWidget(self.groupBox)
        spacerItem = QtGui.QSpacerItem(20, 199, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.horizontalLayout.addWidget(self.widget)
        self.horizontalLayout.setStretch(0, 3)

        self.retranslateUi(MainWidget)
        QtCore.QMetaObject.connectSlotsByName(MainWidget)

    def retranslateUi(self, MainWidget):
        MainWidget.setWindowTitle(_translate("MainWidget", "Form", None))
        self.load_data_btn.setText(_translate("MainWidget", "Load Data", None))
        self.load_bkg_btn.setText(_translate("MainWidget", "Load Bkg", None))
        self.label.setText(_translate("MainWidget", "Scale:", None))
        self.label_2.setText(_translate("MainWidget", "Offset:", None))

from pyqtgraph import GraphicsLayoutWidget

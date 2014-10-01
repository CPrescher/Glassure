# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Main.ui'
#
# Created: Wed Oct  1 17:45:10 2014
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
        MainWidget.resize(737, 439)
        MainWidget.setStyleSheet(_fromUtf8("#mainView, #calibration_tab, #mask_tab, #integration_tab {  \n"
"     background: #3C3C3C;      \n"
"    border: 5px solid #3C3C3C;\n"
" }  \n"
"\n"
"QTabWidget::tab-bar{ \n"
"    alignment: center;\n"
"}\n"
"\n"
"QWidget{\n"
"    color: #F1F1F1;\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:left, QTabBar::tab:right {  \n"
"     background: qlineargradient(spread:pad, x1:1, y1:0, x2:0, y2:0, stop:0 #3C3C3C, stop:1 #505050);\n"
"     border: 1px solid  #5B5B5B;  \n"
"    font: normal 14px;\n"
"    color: #F1F1F1;\n"
"     border-radius:2px;\n"
"    \n"
"    padding: 0px;\n"
"     width: 20px;  \n"
"    min-height:140px;\n"
" }  \n"
"\n"
"\n"
"QTabBar::tab::top, QTabBar::tab::bottom {  \n"
"     background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #3C3C3C, stop:1 #505050);\n"
"     border: 1px solid  #5B5B5B;  \n"
"    border-right: 0px solid white;\n"
"      color: #F1F1F1; \n"
"    font: normal 11px;\n"
"     border-radius:2px;\n"
"     min-width: 80px;  \n"
"    height: 19px;\n"
"    padding: 0px;\n"
"     margin-top: 1px ;\n"
"    margin-right: 1px;\n"
" }  \n"
"QTabBar::tab::left:last, QTabBar::tab::right:last{\n"
"    border-bottom-left-radius: 10px;\n"
"    border-bottom-right-radius: 10px;\n"
"}\n"
"QTabBar::tab:left:first, QTabBar::tab:right:first{\n"
"    border-top-left-radius: 10px;\n"
"    border-top-right-radius: 10px;\n"
"}\n"
"\n"
"QTabWidget, QTabWidget::tab-bar,  QTabWidget::panel, QWidget{  \n"
"     background: #3C3C3C;      \n"
" }  \n"
"\n"
"QTabWidget::tab-bar {\n"
"    alignment: center;\n"
"}\n"
"\n"
" QTabBar::tab:hover {  \n"
"     border: 1px solid #ADADAD;  \n"
" }  \n"
"   \n"
" QTabBar:tab:selected{  \n"
"\n"
"    background: qlineargradient(\n"
"        x1: 0, y1: 1, \n"
"        x2: 0, y2: 0,\n"
"        stop: 0 #727272, \n"
"        stop: 1 #444444\n"
"    );\n"
"     border:1px solid  rgb(255, 120,00);/*#ADADAD; */ \n"
"}\n"
"\n"
"QTabBar::tab:bottom:last, QTabBar::tab:top:last{\n"
"    border-top-right-radius: 10px;\n"
"    border-bottom-right-radius: 10px;\n"
"}\n"
"QTabBar::tab:bottom:first, QTabBar::tab:top:first{\n"
"    border-top-left-radius: 10px;\n"
"    border-bottom-left-radius: 10px;\n"
"}\n"
" QTabBar::tab:top:!selected {  \n"
"    margin-top: 1px;\n"
"    padding-top:1px;\n"
" }  \n"
"QTabBar::tab:bottom:!selected{\n"
"    margin-bottom: 1px;\n"
"    padding-bottom:1px;\n"
"}\n"
"\n"
"QGraphicsView {\n"
"    border-style: none;\n"
"}\n"
"\n"
" QLabel , QCheckBox, QGroupBox, QRadioButton, QListWidget::item, QPushButton, QToolBox::tab, QSpinBox, QDoubleSpinBox , QComboBox{  \n"
"     color: #F1F1F1; \n"
"    font-size: 12px;\n"
" }  \n"
" QCheckBox{  \n"
"     border-radius: 5px;  \n"
" }  \n"
" QRadioButton, QCheckBox {  \n"
"     font-weight: normal;  \n"
"    height: 15px;\n"
" }  \n"
" \n"
" QLineEdit  {  \n"
"     border-radius: 2px;  \n"
"     background: #F1F1F1;  \n"
"     color: black;  \n"
"    height: 18 px;\n"
" }  \n"
"\n"
"QLineEdit::focus{\n"
"    border-style: none;\n"
"     border-radius: 2px;  \n"
"     background: #F1F1F1;  \n"
"     color: black;  \n"
"}\n"
"\n"
"QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled{\n"
"    color:rgb(148, 148, 148)\n"
"}\n"
"QSpinBox, QDoubleSpinBox {\n"
"    background-color:  #F1F1F1;    \n"
"    color: black;\n"
"    margin-left: -15px;\n"
"    margin-right: -2px;\n"
"    height: 30px;\n"
"}\n"
"\n"
"QComboBox QAbstractItemView{\n"
"    background: #2D2D30;\n"
"    color: #F1F1F1;\n"
"    selection-background-color: rgba(221, 124, 40, 120);\n"
"    border-radius: 5px;\n"
"\n"
"}\n"
"\n"
"QComboBox:!editable {\n"
"    margin-left: 1px;\n"
"    padding-left: 10px;\n"
"    height: 23px;\n"
"    background-color: #3C3C3C;\n"
"}\n"
"\n"
"QComboBox::item{\n"
"    background-color: #3C3C3C;\n"
"}\n"
"\n"
"QComboBox::item::selected {\n"
"    background-color: #505050;\n"
"}\n"
"QToolBox::tab:QToolButton{\n"
"    background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #3C3C3C, stop:1 #505050);\n"
"     border: 1px solid  #5B5B5B;  \n"
"\n"
"     border-radius:2px;\n"
"     padding-right: 10px;  \n"
"    \n"
"      color: #F1F1F1; \n"
"    font-size: 12px;\n"
"    padding: 3px;\n"
"}\n"
"QToolBox::tab:QToolButton{\n"
"    background: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0, stop:0 #3C3C3C, stop:1 #505050);\n"
"     border: 1px solid  #5B5B5B;  \n"
"\n"
"     border-radius:2px;\n"
"     padding-right: 10px;  \n"
"    \n"
"      color: #F1F1F1; \n"
"    font-size: 12px;\n"
"    padding: 3px;\n"
"}\n"
"  \n"
"QPushButton{  \n"
"     color: #F1F1F1;\n"
"     background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #323232, stop:1 #505050);\n"
"     border: 1px solid #5B5B5B;\n"
"     border-radius: 5px; \n"
"     padding-left: 8px;\n"
"height: 18px;\n"
"    padding-right: 8px;   \n"
" }  \n"
"QPushButton:pressed{\n"
"        margin-top: 2px;\n"
"        margin-left: 2px;    \n"
"}\n"
"QPushButton::disabled{\n"
"}\n"
"\n"
"QPushButton::hover{  \n"
"     border:1px solid #ADADAD; \n"
" }  \n"
" \n"
"\n"
"QPushButton::checked{\n"
"    background: qlineargradient(\n"
"        x1: 0, y1: 1, \n"
"        x2: 0, y2: 0,\n"
"        stop: 0 #727272, \n"
"        stop: 1 #444444\n"
"    );\n"
"     border:1px solid  rgb(255, 120,00);\n"
"}\n"
"\n"
"QPushButton::focus {\n"
"    outline: None;\n"
"}\n"
" QGroupBox {  \n"
"     border: 1px solid #ADADAD;  \n"
"     border-radius: 4px;  \n"
"     margin-top: 7px;  \n"
"     padding: 0px  \n"
" }  \n"
" QGroupBox::title {  \n"
"      subcontrol-origin: margin;  \n"
"      left: 20px  \n"
"  }\n"
"\n"
"QSplitter::handle:hover {\n"
"    background: #3C3C3C;\n"
" }\n"
"\n"
"\n"
"QGraphicsView{\n"
"    border-style: none;\n"
"}\n"
"\n"
" QScrollBar:vertical {\n"
"      border: 2px solid #3C3C3C;\n"
"      background: qlineargradient(spread:pad, x1:1, y1:0, x2:0, y2:0, stop:0 #323232, stop:1 #505050);\n"
"      width: 12px;\n"
"      margin: 0px 0px 0px 0px;\n"
"  }\n"
"  QScrollBar::handle:vertical {\n"
"      background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #969696, stop:1 #CACACA);\n"
"     border-radius: 3px;\n"
"      min-height: 20px;\n"
"    padding: 15px;\n"
"  }\n"
"  QScrollBar::add-line:vertical {\n"
"      border: 0px solid grey;\n"
"      height: 0px;\n"
"  }\n"
"\n"
"  QScrollBar::sub-line:vertical {\n"
"      border: 0px solid grey;\n"
"      height: 0px;\n"
"  }\n"
"  QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"      background: none;\n"
"  }\n"
"\n"
"#click_x_lbl, #click_y_lbl, #click_int_lbl, #click_azi_lbl, #click_d_lbl, #click_tth_lbl, #click_q_lbl {\n"
"    color: #00DD00;\n"
"}\n"
"\n"
""))
        self.horizontalLayout = QtGui.QHBoxLayout(MainWidget)
        self.horizontalLayout.setMargin(5)
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
        self.load_data_btn.setFlat(True)
        self.load_data_btn.setObjectName(_fromUtf8("load_data_btn"))
        self.verticalLayout.addWidget(self.load_data_btn)
        self.load_bkg_btn = QtGui.QPushButton(self.widget)
        self.load_bkg_btn.setFlat(True)
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
        self.bkg_offset_step_txt = QtGui.QLineEdit(self.groupBox)
        self.bkg_offset_step_txt.setMinimumSize(QtCore.QSize(42, 0))
        self.bkg_offset_step_txt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.bkg_offset_step_txt.setObjectName(_fromUtf8("bkg_offset_step_txt"))
        self.gridLayout.addWidget(self.bkg_offset_step_txt, 2, 2, 1, 1)
        self.bkg_offset_sb = QtGui.QDoubleSpinBox(self.groupBox)
        self.bkg_offset_sb.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.bkg_offset_sb.setSingleStep(10.0)
        self.bkg_offset_sb.setObjectName(_fromUtf8("bkg_offset_sb"))
        self.gridLayout.addWidget(self.bkg_offset_sb, 2, 1, 1, 1)
        self.bkg_scale_sb = QtGui.QDoubleSpinBox(self.groupBox)
        self.bkg_scale_sb.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.bkg_scale_sb.setMinimum(-999999999.0)
        self.bkg_scale_sb.setMaximum(999999999.0)
        self.bkg_scale_sb.setSingleStep(0.01)
        self.bkg_scale_sb.setProperty("value", 1.0)
        self.bkg_scale_sb.setObjectName(_fromUtf8("bkg_scale_sb"))
        self.gridLayout.addWidget(self.bkg_scale_sb, 1, 1, 1, 1)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.bkg_scale_step_txt = QtGui.QLineEdit(self.groupBox)
        self.bkg_scale_step_txt.setMinimumSize(QtCore.QSize(42, 0))
        self.bkg_scale_step_txt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.bkg_scale_step_txt.setObjectName(_fromUtf8("bkg_scale_step_txt"))
        self.gridLayout.addWidget(self.bkg_scale_step_txt, 1, 2, 1, 1)
        self.gridLayout.setColumnStretch(1, 5)
        self.gridLayout.setColumnStretch(2, 3)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtGui.QGroupBox(self.widget)
        self.groupBox_2.setTitle(_fromUtf8(""))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setSpacing(5)
        self.horizontalLayout_2.setMargin(5)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_3 = QtGui.QLabel(self.groupBox_2)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_2.addWidget(self.label_3)
        self.smooth_sb = QtGui.QDoubleSpinBox(self.groupBox_2)
        self.smooth_sb.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.smooth_sb.setMaximum(999999999.0)
        self.smooth_sb.setObjectName(_fromUtf8("smooth_sb"))
        self.horizontalLayout_2.addWidget(self.smooth_sb)
        self.smooth_step_txt = QtGui.QLineEdit(self.groupBox_2)
        self.smooth_step_txt.setMinimumSize(QtCore.QSize(42, 0))
        self.smooth_step_txt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.smooth_step_txt.setObjectName(_fromUtf8("smooth_step_txt"))
        self.horizontalLayout_2.addWidget(self.smooth_step_txt)
        self.verticalLayout.addWidget(self.groupBox_2)
        spacerItem = QtGui.QSpacerItem(20, 8, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.groupBox_3 = QtGui.QGroupBox(self.widget)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox_3)
        self.gridLayout_2.setMargin(5)
        self.gridLayout_2.setHorizontalSpacing(5)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.tableWidget = QtGui.QTableWidget(self.groupBox_3)
        self.tableWidget.setObjectName(_fromUtf8("tableWidget"))
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.gridLayout_2.addWidget(self.tableWidget, 1, 0, 1, 2)
        self.pushButton_2 = QtGui.QPushButton(self.groupBox_3)
        self.pushButton_2.setFlat(True)
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.gridLayout_2.addWidget(self.pushButton_2, 0, 1, 1, 1)
        self.pushButton = QtGui.QPushButton(self.groupBox_3)
        self.pushButton.setFlat(True)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.gridLayout_2.addWidget(self.pushButton, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_3)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.horizontalLayout.addWidget(self.widget)
        self.horizontalLayout.setStretch(0, 3)

        self.retranslateUi(MainWidget)
        QtCore.QMetaObject.connectSlotsByName(MainWidget)

    def retranslateUi(self, MainWidget):
        MainWidget.setWindowTitle(_translate("MainWidget", "Form", None))
        self.load_data_btn.setText(_translate("MainWidget", "Load Data", None))
        self.load_bkg_btn.setText(_translate("MainWidget", "Load Bkg", None))
        self.label.setText(_translate("MainWidget", "Scale:", None))
        self.bkg_offset_step_txt.setText(_translate("MainWidget", "10", None))
        self.label_2.setText(_translate("MainWidget", "Offset:", None))
        self.bkg_scale_step_txt.setText(_translate("MainWidget", "0.01", None))
        self.label_3.setText(_translate("MainWidget", "Smooth:", None))
        self.smooth_step_txt.setText(_translate("MainWidget", "1", None))
        self.groupBox_3.setTitle(_translate("MainWidget", "Composition", None))
        self.pushButton_2.setText(_translate("MainWidget", "Delete", None))
        self.pushButton.setText(_translate("MainWidget", "Add", None))

from pyqtgraph import GraphicsLayoutWidget

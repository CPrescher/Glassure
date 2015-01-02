# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

from PyQt4 import QtGui

class ExpandableBox(QtGui.QWidget):
    def __init__(self, content_widget, title=''):
        super(ExpandableBox, self).__init__()

        self._vlayout = QtGui.QVBoxLayout()
        self._vlayout.setContentsMargins(0, 0, 0, 0)
        self._vlayout.setSpacing(0)
        self._head_layout = QtGui.QHBoxLayout()
        self._head_layout.setContentsMargins(10, 8, 15, 0)
        self._head_layout.setSpacing(0)


        self.minimize_btn = QtGui.QPushButton("-")
        self.minimize_btn.setFixedHeight(20)
        self.minimize_btn.setFixedWidth(20)
        self.minimize_btn.setObjectName("minimize_btn")

        self._head_layout.addWidget(self.minimize_btn)


        self._head_layout.addSpacing(10)
        self.title_lbl = QtGui.QLabel(title)
        self.title_lbl.setStyleSheet("font: italic 15px;")
        self._head_layout.addWidget(self.title_lbl)

        self.minimized = False

        self.content_widget = content_widget
        self.head_widget = QtGui.QWidget()
        self.head_widget.setLayout(self._head_layout)
        self.head_widget.setObjectName("head_widget")

        self._vlayout.addWidget(self.head_widget)


        self._content_widget = QtGui.QWidget()
        self._content_layout = QtGui.QVBoxLayout()
        self._content_layout.setContentsMargins(8,8,8,8)
        self._content_layout.setSpacing(0)
        self._content_layout.addWidget(self.content_widget)
        self._content_widget.setLayout(self._content_layout)

        self._vlayout.addWidget(self._content_widget)
        self._content_widget.setObjectName("content_widget")

        self.setLayout(self._vlayout)

        self.setStyleSheet(
            """
            QLabel, #head_widget{
                background: #303030;
            }
            #head_widget{
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border: 2px solid #666;
                border-bottom: 1px solid #666;
            }
            """
        )
        self._content_widget.setStyleSheet(
            """
            QLabel, QGroupBox, #content_widget{
                background: #3B3B3B;
            }
            #content_widget{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border: 2px solid #666;
                border-top: None;
            }
            """
        )
        self.head_widget.setStyleSheet(
            """
            #minimize_btn{
                border-radius:0px;
                padding: 0px;
                margin: 0px;
                margin-bottom: 2px;
                margin-left: 2px;
                border-top-left-radius: 5px;
            }
            """
        )

        self.minimize_btn.clicked.connect(self.change_state)

    def change_state(self):
        if self.minimized:
            self._content_widget.show()
            self.minimized = False
            self.minimize_btn.setText("-")
        else:
            self._content_widget.hide()
            self.minimized = True
            self.minimize_btn.setText("+")
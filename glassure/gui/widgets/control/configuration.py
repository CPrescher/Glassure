# -*- coding: utf-8 -*-

from functools import partial

from ...qt import QtCore, QtWidgets, Signal
from ..custom import FlatButton, ListTableWidget


class ConfigurationWidget(QtWidgets.QWidget):
    configuration_color_btn_clicked = Signal(int, QtWidgets.QWidget)
    configuration_show_cb_state_changed = Signal(int, bool)
    configuration_name_changed = Signal(int, str)

    def __init__(self, *args):
        super(ConfigurationWidget, self).__init__(*args)

        self._create_widgets()
        self._create_layout()
        self._style_widgets()

        self.configuration_show_cbs = []
        self.configuration_color_btns = []

    def _create_widgets(self):
        self.freeze_btn = QtWidgets.QPushButton("Freeze")
        self.remove_btn = QtWidgets.QPushButton("Remove")
        self.configuration_tw = ListTableWidget(columns=3)
        self.configuration_tw.setObjectName('configuration_tw')

    def _create_layout(self):
        self._button_layout = QtWidgets.QHBoxLayout()
        self._button_layout.addWidget(self.freeze_btn)
        self._button_layout.addWidget(self.remove_btn)

        self._main_layout = QtWidgets.QVBoxLayout()
        self._main_layout.addLayout(self._button_layout)
        self._main_layout.addWidget(self.configuration_tw)

        self.setLayout(self._main_layout)

    def _style_widgets(self):
        self.setStyleSheet("""
            #configuration_tw QPushButton {
                margin-top: 4;
                max-width: 7;
                max-height: 16;
            }
        """)

    def add_configuration(self, name, color):
        self.configuration_tw.blockSignals(True)
        current_rows = self.configuration_tw.rowCount()
        self.configuration_tw.setRowCount(current_rows + 1)

        show_cb = QtWidgets.QCheckBox()
        show_cb.setChecked(True)
        show_cb.stateChanged.connect(partial(self.configuration_show_cb_changed, show_cb))
        show_cb.setStyleSheet("background-color: transparent")
        self.configuration_tw.setCellWidget(current_rows, 0, show_cb)
        self.configuration_show_cbs.append(show_cb)

        color_button = FlatButton()
        color_button.setStyleSheet("background-color: " + color)
        color_button.clicked.connect(partial(self.configuration_color_btn_click, color_button))
        self.configuration_tw.setCellWidget(current_rows, 1, color_button)
        self.configuration_color_btns.append(color_button)

        name_item = QtWidgets.QTableWidgetItem(name)
        name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
        self.configuration_tw.setItem(current_rows, 2, QtWidgets.QTableWidgetItem(name))

        self.configuration_tw.setColumnWidth(0, 20)
        self.configuration_tw.setColumnWidth(1, 25)
        self.configuration_tw.setRowHeight(current_rows, 25)
        self.select_configuration(current_rows)
        self.configuration_tw.blockSignals(False)

    def select_configuration(self, ind):
        if self.configuration_tw.rowCount() > 0:
            self.configuration_tw.selectRow(ind)

    def get_selected_configuration_row(self):
        selected = self.configuration_tw.selectionModel().selectedRows()
        try:
            row = selected[0].row()
        except IndexError:
            row = -1
        return row

    def remove_configuration(self, ind):
        if self.configuration_tw.rowCount() == 0:
            return

        self.configuration_tw.blockSignals(True)
        self.configuration_tw.removeRow(ind)
        self.configuration_tw.blockSignals(False)

        self.configuration_show_cbs.remove(self.configuration_show_cbs[ind])
        self.configuration_color_btns.remove(self.configuration_color_btns[ind])

        if self.configuration_tw.rowCount() > ind:
            self.select_configuration(ind)
        else:
            self.select_configuration(self.configuration_tw.rowCount() - 1)

    def clear_configuration_tw(self):
        self.configuration_tw.clear()
        self.configuration_tw.setRowCount(0)

        self.configuration_show_cbs = []
        self.configuration_color_btns = []

    def configuration_color_btn_click(self, button):
        self.configuration_color_btn_clicked.emit(self.configuration_color_btns.index(button), button)

    def configuration_show_cb_changed(self, checkbox):
        self.configuration_show_cb_state_changed.emit(self.configuration_show_cbs.index(checkbox), checkbox.isChecked())

    def configuration_show_cb_set_checked(self, ind, state):
        checkbox = self.configuration_show_cbs[ind]
        checkbox.setChecked(state)

    def configuration_show_cb_is_checked(self, ind):
        checkbox = self.configuration_show_cbs[ind]
        return checkbox.isChecked()

    def configuration_label_editingFinished(self, row, col):
        label_item = self.configuration_tw.item(row, col)
        self.configuration_name_changed.emit(row, str(label_item.text()))

# -*- coding: utf-8 -*-

import pyqtgraph as pg
import numpy as np
from ...qt import QtCore, QtWidgets, QtGui, Signal


class PatternWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(PatternWidget, self).__init__(*args, **kwargs)
        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.create_plots()
        self.style_plots()
        self.create_items()

        self.mouse_position_widget = MousePositionWidget()
        self._layout.addWidget(self.mouse_position_widget)

        self.create_signals()

        self.setLayout(self._layout)

    def create_plots(self):
        self.pg_layout_widget = pg.GraphicsLayoutWidget()
        self.pg_layout = pg.GraphicsLayout()
        self.pg_layout.setContentsMargins(0, 0, 0, 0)
        self.pg_layout_widget.setContentsMargins(0, 0, 0, 0)

        self.pattern_plot = ModifiedPlotItem()
        self.sq_plot = ModifiedPlotItem()
        self.gr_plot = ModifiedPlotItem()

        self.pg_layout.addItem(self.pattern_plot, 0, 0)
        self.pg_layout.addItem(self.sq_plot, 1, 0)
        self.pg_layout.addItem(self.gr_plot, 2, 0)

        self.pg_layout_widget.addItem(self.pg_layout)

        self._layout.addWidget(self.pg_layout_widget)

    def style_plots(self):
        self.pattern_plot.setLabel('bottom', text='Q (1/A)')
        self.pattern_plot.setLabel('left', text='Int (a.u.)')

        self.sq_plot.setLabel('bottom', text='Q (1/A)')
        self.sq_plot.setLabel('left', text='S(Q)')

        self.gr_plot.setLabel('bottom', text='r (A)')
        self.gr_plot.setLabel('left', text='g(r)')

    def create_items(self):
        self.pattern_item = pg.PlotDataItem(pen=pg.mkPen('w', width=1.5))
        self.bkg_item = pg.PlotDataItem(pen=pg.mkPen('r', width=1.5, style=QtCore.Qt.DashLine))
        self.pattern_plot.addItem(self.pattern_item)
        self.pattern_plot.addItem(self.bkg_item)

        self.sq_items = []
        self.sq_show = []
        self.add_sq_item()

        self.gr_items = []
        self.gr_show = []
        self.add_gr_item()

    def add_sq_item(self, color='w', show=True):
        self.sq_items.append(pg.PlotDataItem([], [], pen=pg.mkPen(color=color, width=1.5)))
        self.sq_show.append(show)
        if show:
            self.sq_plot.addItem(self.sq_items[-1])

    def add_gr_item(self, color='w', show=True):
        self.gr_items.append(pg.PlotDataItem([], [], pen=pg.mkPen(color=color, width=1.5)))
        self.gr_show.append(show)
        if show:
            self.gr_plot.addItem(self.gr_items[-1])

    def remove_sq_item(self, ind=-1):
        self.sq_plot.removeItem(self.sq_items[ind])
        del self.sq_items[ind]
        del self.sq_show[ind]

    def remove_gr_item(self, ind=-1):
        self.gr_plot.removeItem(self.gr_items[ind])
        del self.gr_items[ind]
        del self.gr_show[ind]

    def create_signals(self):
        self.pattern_plot.connect_mouse_move_event()
        self.sq_plot.connect_mouse_move_event()
        self.gr_plot.connect_mouse_move_event()
        self.pattern_plot.mouse_moved.connect(self.mouse_moved)
        self.sq_plot.mouse_moved.connect(self.mouse_moved)
        self.gr_plot.mouse_moved.connect(self.mouse_moved)

    def mouse_moved(self, x, y):
        self.mouse_position_widget.x_value_lbl.setText("{:9.3f}".format(x))
        self.mouse_position_widget.y_value_lbl.setText("{:9.3f}".format(y))

    def plot_pattern(self, pattern):
        x, y = pattern.data
        self.pattern_item.setData(x=x, y=y)

    def plot_bkg(self, pattern):
        x, y = pattern.data
        self.bkg_item.setData(x=x, y=y)

    def set_sq_pattern(self, pattern, ind):
        x, y = pattern.data
        self.sq_items[ind].setData(x=x, y=y)

    def set_gr_pattern(self, pattern, ind):
        x, y = pattern.data
        self.gr_items[ind].setData(x=x, y=y)

    def set_color(self, color, ind):
        self.sq_items[ind].setPen(pg.mkPen(color=color, width=1.5))
        self.gr_items[ind].setPen(pg.mkPen(color=color, width=1.5))
        self.sq_items[ind].setZValue(0)
        self.gr_items[ind].setZValue(0)

    def activate_ind(self, ind):
        self.sq_items[ind].setPen(pg.mkPen(color='w', width=2))
        self.gr_items[ind].setPen(pg.mkPen(color='w', width=2))
        self.sq_items[ind].setZValue(100)
        self.gr_items[ind].setZValue(100)

    def hide_sq(self, ind):
        self.sq_plot.removeItem(self.sq_items[ind])
        self.sq_show[ind] = False

    def hide_gr(self, ind):
        self.gr_plot.removeItem(self.gr_items[ind])
        self.gr_show[ind] = False

    def show_sq(self, ind):
        self.sq_plot.addItem(self.sq_items[ind])
        self.sq_show[ind] = True

    def show_gr(self, ind):
        self.gr_plot.addItem(self.gr_items[ind])
        self.gr_show[ind] = True

    def set_configuration_color(self, color, ind):
        self.sq_items[ind].setPen(pg.mkPen(color=color, width=1.5))
        self.gr_items[ind].setPen(pg.mkPen(color=color, width=1.5))


class ModifiedPlotItem(pg.PlotItem):
    mouse_moved = Signal(float, float)
    mouse_left_clicked = Signal(float, float)
    range_changed = Signal(list)

    def __init__(self, *args, **kwargs):
        super(ModifiedPlotItem, self).__init__(*args, **kwargs)

        self.modify_mouse_behavior()

    def modify_mouse_behavior(self):
        self.vb.mouseClickEvent = self.mouse_click_event
        self.vb.mouseDragEvent = self.mouse_drag_event
        self.vb.mouseDoubleClickEvent = self.mouse_double_click_event
        self.vb.wheelEvent = self.wheel_event
        self.range_changed_timer = QtCore.QTimer()
        self.range_changed_timer.timeout.connect(self.emit_sig_range_changed)
        self.range_changed_timer.setInterval(30)
        self.last_view_range = np.array(self.vb.viewRange())

    def connect_mouse_move_event(self):
        self.scene().sigMouseMoved.connect(self.mouse_move_event)

    def mouse_move_event(self, pos):
        if self.sceneBoundingRect().contains(pos):
            pos = self.vb.mapSceneToView(pos)
            self.mouse_moved.emit(pos.x(), pos.y())

    def mouse_click_event(self, ev):
        if ev.button() == QtCore.Qt.RightButton or \
                (ev.button() == QtCore.Qt.LeftButton and
                         ev.modifiers() & QtCore.Qt.ControlModifier):
            self.vb.scaleBy(2)
            self.vb.sigRangeChangedManually.emit(self.vb.state['mouseEnabled'])
        elif ev.button() == QtCore.Qt.LeftButton:
            if self.sceneBoundingRect().contains(ev.pos()):
                pos = self.vb.mapToView(ev.pos())
                x = pos.x()
                y = pos.y()
                self.mouse_left_clicked.emit(x, y)

    def mouse_double_click_event(self, ev):
        if (ev.button() == QtCore.Qt.RightButton) or (ev.button() == QtCore.Qt.LeftButton and
                                                              ev.modifiers() & QtCore.Qt.ControlModifier):
            self.vb.autoRange()
            self.vb.enableAutoRange()
            self._auto_range = True
            self.vb.sigRangeChangedManually.emit(self.vb.state['mouseEnabled'])

    def mouse_drag_event(self, ev, axis=None):
        # most of this code is copied behavior mouse drag from the original code
        ev.accept()
        pos = ev.pos()
        last_pos = ev.lastPos()
        dif = pos - last_pos
        dif *= -1

        if ev.button() == QtCore.Qt.RightButton or \
                (ev.button() == QtCore.Qt.LeftButton and ev.modifiers() & QtCore.Qt.ControlModifier):
            # determine the amount of translation
            tr = dif
            tr = self.vb.mapToView(tr) - self.vb.mapToView(pg.Point(0, 0))
            x = tr.x()
            y = tr.y()
            self.vb.translateBy(x=x, y=y)
            if ev.start:
                self.range_changed_timer.start()
            if ev.isFinish():
                self.range_changed_timer.stop()
                self.emit_sig_range_changed()
        else:
            if ev.isFinish():  # This is the final move in the drag; change the view scale now
                self._auto_range = False
                self.vb.enableAutoRange(enable=False)
                self.vb.rbScaleBox.hide()
                ax = QtCore.QRectF(pg.Point(ev.buttonDownPos(ev.button())), pg.Point(pos))
                ax = self.vb.childGroup.mapRectFromParent(ax)
                self.vb.showAxRect(ax)
                self.vb.axHistoryPointer += 1
                self.vb.axHistory = self.vb.axHistory[:self.vb.axHistoryPointer] + [ax]
                self.vb.sigRangeChangedManually.emit(self.vb.state['mouseEnabled'])
            else:
                # update shape of scale box
                self.vb.updateScaleBox(ev.buttonDownPos(), ev.pos())

    def emit_sig_range_changed(self):
        new_view_range = np.array(self.vb.viewRange())
        if not np.array_equal(self.last_view_range, new_view_range):
            self.vb.sigRangeChangedManually.emit(self.vb.state['mouseEnabled'])
            self.last_view_range = new_view_range

    def wheel_event(self, ev, axis=None, *args):
        pg.ViewBox.wheelEvent(self.vb, ev, axis)
        self.vb.sigRangeChangedManually.emit(self.vb.state['mouseEnabled'])


class MousePositionWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(MousePositionWidget, self).__init__()

        self.horizontal_layout = QtWidgets.QHBoxLayout()
        self.horizontal_layout.setContentsMargins(0, 0, 0, 5)
        self.horizontal_layout.setSpacing(5)
        self.x_unit_lbl = QtWidgets.QLabel('x:')
        self.x_value_lbl = QtWidgets.QLabel('0.00')

        self.y_unit_lbl = QtWidgets.QLabel('y:')
        self.y_value_lbl = QtWidgets.QLabel('0.00')

        self.x_unit_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.x_value_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.y_unit_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        self.y_value_lbl.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)

        self.x_unit_lbl.setFixedWidth(30)
        self.y_unit_lbl.setFixedWidth(30)

        self.x_value_lbl.setFixedWidth(50)
        self.y_value_lbl.setFixedWidth(50)

        self.save_sq_btn = QtWidgets.QPushButton("Save S(Q)")
        self.save_sq_btn.setFlat(True)
        self.save_gr_btn = QtWidgets.QPushButton("Save g(r)")
        self.save_gr_btn.setFlat(True)

        self.horizontal_layout.addWidget(self.x_unit_lbl)
        self.horizontal_layout.addWidget(self.x_value_lbl)
        self.horizontal_layout.addWidget(self.y_unit_lbl)
        self.horizontal_layout.addWidget(self.y_value_lbl)
        self.horizontal_layout.addSpacerItem(QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding,
                                                                   QtWidgets.QSizePolicy.Fixed))

        self.horizontal_layout.addWidget(self.save_sq_btn)
        self.horizontal_layout.addWidget(self.save_gr_btn)
        self.setLayout(self.horizontal_layout)

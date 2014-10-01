# -*- coding: utf8 -*-
__author__ = 'Clemens Prescher'

import time
import pyqtgraph as pg
import numpy as np
from PyQt4 import QtCore, QtGui
from pyqtgraph.exporters.ImageExporter import ImageExporter
from pyqtgraph.exporters.SVGExporter import SVGExporter

# TODO refactoring of the 3 lists: overlays, overlay_names, overlay_show,
# should probably a class, making it more readable


class SpectrumWidget(QtCore.QObject):
    mouse_moved = QtCore.pyqtSignal(float, float)
    mouse_left_clicked = QtCore.pyqtSignal(float, float)
    range_changed = QtCore.pyqtSignal(list)

    def __init__(self, pg_layout, x_label = '', y_label = ''):
        super(SpectrumWidget, self).__init__()
        self.pg_layout = pg_layout
        self.create_graphics()
        self.create_main_plot()
        self.create_pos_line()
        self.modify_mouse_behavior()
        self._auto_range = True
        self.set_labels(x_label, y_label)

    def create_graphics(self):
        self.spectrum_plot = self.pg_layout.addPlot()
        self.view_box = self.spectrum_plot.vb

    def set_labels(self, x_label='', y_label=''):
        if x_label != 1:
            self.spectrum_plot.showLabel('bottom', True)
            self.spectrum_plot.setLabel('bottom', x_label)
        else:
            self.spectrum_plot.showLabel('bottom', False)

        if y_label != 1:
            self.spectrum_plot.showLabel('left', True)
            self.spectrum_plot.setLabel('left', y_label)
        else:
            self.spectrum_plot.showLabel('left', False)

    def create_main_plot(self):
        self.plot_item = pg.PlotDataItem(np.linspace(0, 10), np.sin(np.linspace(10, 3)),
                                         pen=pg.mkPen(color=(255, 255, 255), width=2))
        self.spectrum_plot.addItem(self.plot_item)

    def create_pos_line(self):
        self.pos_line = pg.InfiniteLine(pen=pg.mkPen(color=(0, 255, 0), width=1.5, style=QtCore.Qt.DashLine))
        self.spectrum_plot.addItem(self.pos_line)

    def set_pos_line(self, x):
        self.pos_line.setPos(x)

    def get_pos_line(self):
        return self.pos_line.value()

    def plot_data(self, x, y, name=None):
        self.plot_item.setData(x, y)
        if name is not None:
            self.legend.legendItems[0][1].setText(name)
            self.plot_name = name
        self.update_graph_limits()

    def update_graph_limits(self):
        x_range = list(self.plot_item.dataBounds(0))
        self.view_box.setLimits(xMin=x_range[0], xMax=x_range[1],
                                minXRange=x_range[0], maxXRange=x_range[1])\


    def save_svg(self, filename):
        self._invert_color()
        previous_label = None
        if self.spectrum_plot.getAxis('bottom').labelText == u'2θ':
            previous_label = (u'2θ', '°')
            self.spectrum_plot.setLabel('bottom', '2th_deg', '')
        exporter = SVGExporter(self.spectrum_plot)
        exporter.export(filename)
        self._norm_color()
        if previous_label is not None:
            self.spectrum_plot.setLabel('bottom', previous_label[0], previous_label[1])

    def _invert_color(self):
        self.spectrum_plot.getAxis('bottom').setPen('k')
        self.spectrum_plot.getAxis('left').setPen('k')
        self.plot_item.setPen('k')
        self.legend.legendItems[0][1].setAttr('color', '000')
        self.legend.legendItems[0][1].setText(self.legend.legendItems[0][1].text)

    def _norm_color(self):
        self.spectrum_plot.getAxis('bottom').setPen('w')
        self.spectrum_plot.getAxis('left').setPen('w')
        self.plot_item.setPen('w')
        self.legend.legendItems[0][1].setAttr('color', 'FFF')
        self.legend.legendItems[0][1].setText(self.legend.legendItems[0][1].text)

    def mouseMoved(self, pos):
        pos = self.plot_item.mapFromScene(pos)
        self.mouse_moved.emit(pos.x(), pos.y())

    def modify_mouse_behavior(self):
        # different mouse handlers
        self.view_box.setMouseMode(self.view_box.RectMode)

        self.pg_layout.scene().sigMouseMoved.connect(self.mouseMoved)
        self.view_box.mouseClickEvent = self.myMouseClickEvent
        self.view_box.mouseDragEvent = self.myMouseDragEvent
        self.view_box.mouseDoubleClickEvent = self.myMouseDoubleClickEvent
        self.view_box.wheelEvent = self.myWheelEvent

        # create sigranged changed timer for right click drag
        # if not using the timer the signals are fired too often and
        # the computer becomes slow...
        self.range_changed_timer = QtCore.QTimer()
        self.range_changed_timer.timeout.connect(self.emit_sig_range_changed)
        self.range_changed_timer.setInterval(30)
        self.last_view_range = np.array(self.view_box.viewRange())

    def myMouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton or \
                (ev.button() == QtCore.Qt.LeftButton and
                 ev.modifiers() & QtCore.Qt.ControlModifier):
            view_range = np.array(self.view_box.viewRange()) * 2
            curve_data = self.plot_item.getData()
            x_range = np.max(curve_data[0]) - np.min(curve_data[0])
            if (view_range[0][1] - view_range[0][0]) > x_range:
                self._auto_range = True
                self.view_box.autoRange()
                self.view_box.enableAutoRange()
            else:
                self._auto_range = False
                self.view_box.scaleBy(2)
            self.view_box.sigRangeChangedManually.emit(self.view_box.state['mouseEnabled'])
        elif ev.button() == QtCore.Qt.LeftButton:
            pos = self.view_box.mapFromScene(ev.pos())
            pos = self.plot_item.mapFromScene(2 * ev.pos() - pos)
            x = pos.x()
            y = pos.y()
            self.mouse_left_clicked.emit(x, y)

    def myMouseDoubleClickEvent(self, ev):
        if (ev.button() == QtCore.Qt.RightButton) or (ev.button() == QtCore.Qt.LeftButton and
                                                      ev.modifiers() & QtCore.Qt.ControlModifier):
            self.view_box.autoRange()
            self.view_box.enableAutoRange()
            self._auto_range = True
            self.view_box.sigRangeChangedManually.emit(self.view_box.state['mouseEnabled'])

    def myMouseDragEvent(self, ev, axis=None):
        # most of this code is copied behavior mouse drag from the original code
        ev.accept()
        pos = ev.pos()
        lastPos = ev.lastPos()
        dif = pos - lastPos
        dif *= -1

        if ev.button() == QtCore.Qt.RightButton or \
                (ev.button() == QtCore.Qt.LeftButton and
                 ev.modifiers() & QtCore.Qt.ControlModifier):
            # determine the amount of translation
            tr = dif
            tr = self.view_box.mapToView(tr) - self.view_box.mapToView(pg.Point(0, 0))
            x = tr.x()
            y = tr.y()
            self.view_box.translateBy(x=x, y=y)
            if ev.start:
                self.range_changed_timer.start()
            if ev.isFinish():
                self.range_changed_timer.stop()
                self.emit_sig_range_changed()
        else:
            if ev.isFinish():  # This is the final move in the drag; change the view scale now
                self._auto_range = False
                self.view_box.enableAutoRange(enable=False)
                self.view_box.rbScaleBox.hide()
                ax = QtCore.QRectF(pg.Point(ev.buttonDownPos(ev.button())), pg.Point(pos))
                ax = self.view_box.childGroup.mapRectFromParent(ax)
                self.view_box.showAxRect(ax)
                self.view_box.axHistoryPointer += 1
                self.view_box.axHistory = self.view_box.axHistory[:self.view_box.axHistoryPointer] + [ax]
                self.view_box.sigRangeChangedManually.emit(self.view_box.state['mouseEnabled'])
            else:
                # update shape of scale box
                self.view_box.updateScaleBox(ev.buttonDownPos(), ev.pos())

    def emit_sig_range_changed(self):
        new_view_range = np.array(self.view_box.viewRange())
        if not np.array_equal(self.last_view_range, new_view_range):
            self.view_box.sigRangeChangedManually.emit(self.view_box.state['mouseEnabled'])
            self.last_view_range = new_view_range

    def myWheelEvent(self, ev, axis=None, *args):
        if ev.delta() > 0:
            pg.ViewBox.wheelEvent(self.view_box, ev, axis)

            self._auto_range = False
            # axis_range = self.spectrum_plot.viewRange()
            # self.range_changed.emit(axis_range)
        else:
            if self._auto_range is not True:
                view_range = np.array(self.view_box.viewRange())
                curve_data = self.plot_item.getData()
                x_range = np.max(curve_data[0]) - np.min(curve_data[0])
                y_range = np.max(curve_data[1]) - np.min(curve_data[1])
                if (view_range[0][1] - view_range[0][0]) >= x_range and \
                        (view_range[1][1] - view_range[1][0]) >= y_range:
                    self.view_box.autoRange()
                    self.view_box.enableAutoRange()
                    self._auto_range = True
                else:
                    self._auto_range = False
                    pg.ViewBox.wheelEvent(self.view_box, ev)
        self.view_box.sigRangeChangedManually.emit(self.view_box.state['mouseEnabled'])
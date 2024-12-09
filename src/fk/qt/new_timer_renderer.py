#  Flowkeeper - Pomodoro timer for power users and teams
#  Copyright (c) 2023 Constantine Kulak
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
import math

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPen, Qt, QConicalGradient


class NewTimerRenderer(QtCore.QObject):
    _widget: QtWidgets.QWidget | None
    _bg_brush: QtGui.QBrush | QtGui.QColor | None
    _bg_pen: QtGui.QPen | QtGui.QColor | None
    _margin: float
    _thickness: float
    _my_value: float | None
    _is_set: bool
    _is_work: bool
    _font: QtGui.QFont | None
    _font_color: QtGui.QColor | None
    _pen_width: int
    _hue_work: int
    _hue_rest: int
    _pen_border: QPen

    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_pen: QtGui.QPen | QtGui.QColor | None,
                 bg_brush: QtGui.QBrush | QtGui.QColor | None,
                 margin: float,
                 thickness: float,
                 font: QtGui.QFont | None,
                 font_color: QtGui.QColor | None,
                 pen_width: int,
                 hue_work: int,
                 hue_rest: int):
        super(NewTimerRenderer, self).__init__(parent)
        self._widget = parent
        self._bg_brush = bg_brush
        self._bg_pen = bg_pen
        self._margin = margin
        self._thickness = thickness
        self._font = font
        self._font_color = font_color
        self._pen_width = pen_width
        self._hue_work = hue_work
        self._hue_rest = hue_rest

        self._pen_border = QPen()
        self._pen_border.setWidth(pen_width)
        if bg_pen is not None:
            self._pen_border.setColor(bg_pen)

        self.reset()

    def set_hues(self, hue_work, hue_rest):
        self._hue_work = hue_work
        self._hue_rest = hue_rest

    def set_colors(self, fg_color: QColor, bg_color: QColor):
        self._bg_pen = fg_color
        self._pen_border.setColor(fg_color)
        self._bg_brush = bg_color
        self._font_color = fg_color

    def reset(self) -> None:
        self._my_value = 0
        self._is_work = True
        self._is_set = True

    def set_values(self, my: float | None, team: float | None = None, is_work: bool = True) -> None:
        self._my_value = my
        self._is_work = is_work
        self._is_set = True

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        if not self._is_set:
            painter.end()
            return

        rw = rect.width()
        rh = rect.height()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        margin = 0.15
        my_rect = QtCore.QRect(rect.left() + int(rw * margin),
                               rect.top() + int(rh * margin),
                               rect.width() - int(2 * rw * margin),
                               rect.height() - int(2 * rh * margin))

        # Draw the outlines
        outline = QPen(QColor("#9fa0a1"), rw * margin / 2)
        painter.setPen(outline)
        painter.drawLine(rect.center().x(),
                         rect.top() + rh * margin / 2,
                         rect.center().x(),
                         rect.top() + int(rh * margin))
        outline.setWidth(rw * margin / 4)
        outline.setColor(QColor("#eff0f1"))
        painter.drawEllipse(my_rect)
        painter.setPen(outline)
        painter.drawLine(rect.center().x() + rw * margin / 8,
                         rect.top() + rh * margin / 2,
                         rect.center().x() + rw * margin / 8,
                         rect.top() + int(rh * margin))
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(outline)
        painter.drawLine(rect.center().x() - int(rw * margin / 2),
                         rect.top() + outline.width(),
                         rect.center().x() + int(rw * margin / 2),
                         rect.top() + outline.width())
        outline.setColor(QColor("#9fa0a1"))
        painter.setPen(outline)
        painter.drawLine(rect.center().x() - int(rw * margin / 2),
                         rect.top() + outline.width(),
                         rect.center().x() - rw * margin / 8,
                         rect.top() + outline.width())

        # Add a "darker" overlay for the "glass" looks
        painter.setPen(Qt.PenStyle.NoPen)
        center = my_rect.center()
        center.setX(center.x())
        gradient = QConicalGradient(center, 90)
        gradient.setColorAt(0, QColor.fromHsl(0, 0, 0, 128))
        gradient.setColorAt(1, QColor.fromHsl(0, 0, 255, 128))
        painter.setBrush(gradient)
        painter.drawEllipse(my_rect.adjusted(-int(rw * margin) / 4, -int(rh * margin) / 4, int(rw * margin) / 4, int(rh * margin) / 4))

        if self._my_value > 0:
            # Draw the sector
            painter.setPen(Qt.PenStyle.NoPen)
            my_hue = self._hue_work if self._is_work else self._hue_rest
            painter.setBrush(QtGui.QColor().fromHsl(my_hue, 255, 128))
            painter.drawPie(my_rect.adjusted(int(rw * margin) / 4, int(rh * margin) / 4, -int(rw * margin) / 4, -int(rh * margin) / 4),
                            int(5760 * (1.0 - self._my_value) + 1440),
                            int(5760 * self._my_value))

        # Draw the "hand"
        outline.setWidth(rw * margin / 2)
        outline.setColor(QColor("#ffffff"))
        painter.setPen(outline)
        c = rect.center()
        radius = (rw * (1 - 3 * margin)) / 2
        painter.drawLine(c, QPoint(c.x() + radius * math.sin(2 * math.pi * self._my_value),
                                   c.y() - radius * math.cos(2 * math.pi * self._my_value)))

        painter.end()

    def eventFilter(self, widget: QtWidgets.QWidget, event: QtCore.QEvent) -> bool:
        if self._widget is None:
            raise Exception("Cannot filter events on a Pixmap")
        if widget == self._widget and event.type() == QtCore.QEvent.Type.Paint:
            painter = QtGui.QPainter(widget)
            rect = widget.contentsRect()
            self.paint(painter, rect)
            return True
        return False

    def repaint(self, painter: QtGui.QPainter = None, rect: QtCore.QRect = None) -> None:
        if self._widget is None:
            self.paint(painter, rect)
        else:
            self._widget.repaint()

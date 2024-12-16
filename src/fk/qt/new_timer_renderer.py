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
from PySide6.QtGui import QColor, QPen, Qt, QConicalGradient, QBrush


class NewTimerRenderer(QtCore.QObject):
    _widget: QtWidgets.QWidget | None
    _my_value: float | None
    _is_set: bool
    _is_work: bool
    _hue_work: int
    _hue_rest: int
    _is_dark: bool

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
                 hue_rest: int,
                 is_dark: bool):
        super(NewTimerRenderer, self).__init__(parent)
        self._widget = parent
        self._hue_work = hue_work
        self._hue_rest = hue_rest
        self._is_dark = is_dark
        self.reset()

    def set_colors(self, fg_color: QColor, bg_color: QColor):
        pass

    def set_hues(self, hue_work, hue_rest):
        self._hue_work = hue_work
        self._hue_rest = hue_rest

    def reset(self) -> None:
        self._my_value = 0
        self._is_work = True
        self._is_set = True

    def set_values(self, my: float | None, team: float | None = None, is_work: bool = True) -> None:
        self._my_value = my
        self._is_work = is_work
        self._is_set = True

    def _outline_pen(self, size: float) -> QPen:
        th2 = size * 0.12
        outline = QPen(QColor("#ff5555" if self._is_work else '#55ff55'), th2)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        return outline

    def _hand_pen(self, size: float) -> QPen:
        th2 = size * 0.12
        hand = QPen(QColor("#ffffff" if self._is_dark else '#000000'), th2)
        hand.setCapStyle(Qt.PenCapStyle.RoundCap)
        return hand

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        if not self._is_set:
            painter.end()
            return

        size = rect.width() * 0.72
        radius = size / 2
        hand_length = size / 2 - 2
        sin = math.sin(2 * math.pi * self._my_value)
        cos = math.cos(2 * math.pi * self._my_value)
        center = rect.center()
        center.setY(center.y() + 1)
        cx = center.x()
        cy = center.y()
        th1 = size * 0.05
        th2 = size * 0.12
        th4 = size * 0.2

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        outline = self._outline_pen(size)
        hand = self._hand_pen(size)

        # Outline
        painter.setPen(outline)
        painter.drawEllipse(center, radius, radius)

        # Add a "darker" overlay for the "glass" looks
        # gradient = QConicalGradient(center, 90)
        # gradient.setColorAt(0, QColor.fromHsl(0, 0, 0, 128))
        # gradient.setColorAt(1, QColor.fromHsl(0, 0, 255, 128))
        # painter.setBrush(gradient)
        # painter.drawEllipse(center, radius, radius)

        # Draw the "hand"
        painter.setPen(hand)
        hx = cx + hand_length * sin
        hy = cy - hand_length * cos
        painter.drawLine(center, QPoint(hx, hy))

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

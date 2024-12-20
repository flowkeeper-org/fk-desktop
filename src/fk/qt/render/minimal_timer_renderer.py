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
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QColor, QPen, Qt

from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer


class MinimalTimerRenderer(AbstractTimerRenderer):
    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None):
        super(MinimalTimerRenderer, self).__init__(parent, bg_color, fg_color)

    def _outline_pen(self, size: float) -> QPen:
        th2 = size * 0.12
        outline = QPen(QColor("#ff5555" if self.get_mode() == 'working' else '#55ff55'), th2)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        return outline

    def _hand_pen(self, size: float) -> QPen:
        th2 = size * 0.12
        hand = QPen(QColor(self._fg_color), th2)
        hand.setCapStyle(Qt.PenCapStyle.RoundCap)
        return hand

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        size = rect.width() * 0.72
        radius = size / 2
        hand_length = size / 2 - 2
        sin = math.sin(2 * math.pi * self._my_value / self._my_max) if self._my_max != 0 else 0
        cos = math.cos(2 * math.pi * self._my_value / self._my_max) if self._my_max != 0 else 0
        center = rect.center()
        center.setY(center.y() + 1)
        cx = center.x()
        cy = center.y()

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        outline = self._outline_pen(size)
        hand = self._hand_pen(size)

        # Outline
        painter.setPen(outline)
        painter.drawEllipse(center, radius, radius)

        # Draw the "hand"
        painter.setPen(hand)
        hx = cx + hand_length * sin
        hy = cy - hand_length * cos
        painter.drawLine(center, QPointF(hx, hy))

        painter.end()

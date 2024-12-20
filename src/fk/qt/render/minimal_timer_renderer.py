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
from PySide6.QtCore import QPointF, QLineF
from PySide6.QtGui import QColor, QPen, Qt

from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer


class MinimalTimerRenderer(AbstractTimerRenderer):
    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None):
        super(MinimalTimerRenderer, self).__init__(parent, bg_color, fg_color)

    def _dial_pen(self, th: float) -> QPen:
        if self._bg_color.value() < 128:
            # Dark background
            if self.get_mode() == 'working':
                color = '#FF3633'
            elif self.get_mode() == 'resting':
                color = '#5DB6EA'
            else:
                color = '#CECECE'
        else:
            # Light background
            if self.get_mode() == 'working':
                color = '#CC0300'
            elif self.get_mode() == 'resting':
                color = '#1A91D5'
            else:
                color = '#5C6872'
        outline = QPen(QColor(color), th)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        return outline

    def _hand_pen(self, th: float) -> QPen:
        hand = QPen(QColor(self._fg_color), th)
        hand.setCapStyle(Qt.PenCapStyle.RoundCap)
        return hand

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        size = rect.width() * 0.8
        th = size * 0.1
        radius = size / 2
        hand_length = size / 2 - 2
        sin = math.sin(2 * math.pi * self._my_value / self._my_max) if self._my_max != 0 else 0
        cos = math.cos(2 * math.pi * self._my_value / self._my_max) if self._my_max != 0 else 0
        center = rect.center()
        center.setY(center.y() * 1.1)
        cx = center.x()
        cy = center.y()

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Dial
        painter.setPen(self._dial_pen(th))
        painter.drawEllipse(center, radius, radius)
        painter.drawLine(QLineF(cx * 0.8, th / 2, cx * 1.2, th / 2))
        painter.drawLine(QLineF(cx, th / 2 + 1, cx, (rect.width() - size) / 2))

        # Draw the "hand"
        painter.setPen(self._hand_pen(th))
        hx = cx + hand_length * sin
        hy = cy - hand_length * cos
        painter.drawLine(center, QPointF(hx, hy))

        painter.end()

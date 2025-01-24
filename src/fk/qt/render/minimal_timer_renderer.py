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
from PySide6.QtGui import QColor, QPen, Qt, QBrush

from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer, rotate_point


class MinimalTimerRenderer(AbstractTimerRenderer):
    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None,
                 thin: bool = False,
                 small: bool = False):
        super(MinimalTimerRenderer, self).__init__(parent, bg_color, fg_color, thin, small)

    def _dial_pen(self, th: float) -> QPen:
        if self._thin:
            color = self._fg_color
        else:
            if self._bg_color.value() < 128:
                # Dark background
                if self.get_mode() == 'working' or self.get_mode() == 'tracking':
                    color = '#e06666'
                elif self.get_mode() == 'resting':
                    color = '#6d9eeb'
                elif self.get_mode() == 'ready':
                    color = '#00e000'
                else:
                    color = '#ffffff'
            else:
                if self.get_mode() == 'working' or self.get_mode() == 'tracking':
                    color = '#cc0000'
                elif self.get_mode() == 'resting':
                    color = '#3c78d8'
                elif self.get_mode() == 'ready':
                    color = '#006400'
                else:
                    color = '#000000'
        outline = QPen(QColor(color), th)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        return outline

    def _next_brush(self) -> QBrush:
        if self._thin:
            color = self._fg_color
        else:
            if self._bg_color.value() < 128:
                # Dark background
                color = '#00e000'
            else:
                color = '#006400'
        return QBrush(QColor(color))

    def _hand_pen(self, th: float) -> QPen:
        hand = QPen(QColor(self._fg_color), th)
        hand.setCapStyle(Qt.PenCapStyle.RoundCap)
        return hand

    def has_idle_display(self) -> bool:
        return True

    def has_next_display(self) -> bool:
        return True

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        size = rect.width()
        th = size * 0.1
        shift = th / 2
        radius = (size - 2 * shift - th) / 2
        hand_length = radius - 2
        center = rect.center()
        center.setY(center.y() + shift)
        cx = center.x()
        cy = center.y()

        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Dial and "buttons"
        painter.setPen(self._dial_pen(th))
        painter.drawEllipse(center, radius, radius)

        painter.setPen(self._dial_pen(th / 2))
        painter.drawLine(QLineF(cx * 0.8, th / 4, cx * 1.2, th / 4))
        painter.drawLine(QLineF(cx, th / 4 + 1, cx, shift * 2))

        painter.drawLine(QLineF(rotate_point(cx * 0.8, th / 4, cx, cy, math.pi / 4),
                                rotate_point(cx * 1.2, th / 4, cx, cy, math.pi / 4)))
        painter.drawLine(QLineF(rotate_point(cx, th / 4 + 1, cx, cy, math.pi / 4),
                                rotate_point(cx, shift * 2, cx, cy, math.pi / 4)))

        if self._mode == 'ready':
            # Draw the "next arrow"
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._next_brush())
            aspect = 0.666
            painter.drawPolygon([
                QPointF(cx * 0.8, cy - hand_length * aspect),
                QPointF(cx + hand_length * aspect, cy),
                QPointF(cx * 0.8, cy + hand_length * aspect),
            ])
        elif self._mode == 'tracking':
            # Draw a pair of hands
            v = int(self._my_value)
            # 1. Second hand
            seconds = (self._my_value % 60) / 60.0
            sin = math.sin(2 * math.pi * seconds)
            cos = math.cos(2 * math.pi * seconds)
            painter.setPen(self._hand_pen(th / 6))
            pt = QPointF(cx + hand_length * sin,
                         cy - hand_length * cos)
            painter.drawLine(center, pt)
            # 2. Minute hand
            minutes = ((self._my_value / 60) % 60.0) / 60.0
            sin = math.sin(2 * math.pi * minutes)
            cos = math.cos(2 * math.pi * minutes)
            painter.setPen(self._hand_pen(th / 4))
            pt = QPointF(cx + hand_length * 0.75 * sin,
                         cy - hand_length * 0.75 * cos)
            painter.drawLine(center, pt)
            # 3. Hour hand
            hour = ((self._my_value / 60 / 24) % 24) / 24.0
            sin = math.sin(2 * math.pi * hour)
            cos = math.cos(2 * math.pi * hour)
            painter.setPen(self._hand_pen(th / 2))
            pt = QPointF(cx + hand_length * 0.5 * sin,
                         cy - hand_length * 0.5 * cos)
            painter.drawLine(center, pt)
        elif self._mode not in ('working', 'resting'):
            # Draw the "hanging hand"
            painter.drawLine(center, QPointF(cx, cy - hand_length))
        else:
            # Draw the hand
            sin = math.sin(
                2 * math.pi * self._my_value / self._my_max) \
                if self._my_max != 0 and self._my_max is not None \
                else 0
            cos = math.cos(
                2 * math.pi * self._my_value / self._my_max) \
                if self._my_max != 0 and self._my_max is not None \
                else 0
            painter.setPen(self._hand_pen(th / 2))
            hx = cx + hand_length * sin
            hy = cy - hand_length * cos
            pt = QPointF(hx, hy)
            painter.drawLine(center, pt)

        painter.end()

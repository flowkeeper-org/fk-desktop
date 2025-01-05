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
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainterPath, QPen, QPixmap

from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer


class ClassicTimerRenderer(AbstractTimerRenderer):
    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None,
                 thin: bool = False,
                 small: bool = False):
        super(ClassicTimerRenderer, self).__init__(parent, bg_color, fg_color, thin, small)

    def clear_pie(self, painter: QtGui.QPainter, rect: QtCore.QRect, entire: QtCore.QRect) -> None:
        # I also tried painter.setClipRegion(QRegion), but it won't apply antialiasing, looking ugly
        full = QPainterPath()
        full.addRect(entire)
        hole = QPainterPath()
        w = 1
        hole_rect = QRect(rect.x() + w, rect.y() + w, rect.width() - 2 * w, rect.height() - 2 * w)
        hole.addEllipse(hole_rect)
        full = full.subtracted(hole)
        painter.setClipPath(full)

    def clear_pie_outline(self, painter: QtGui.QPainter, rect: QtCore.QRect, entire: QtCore.QRect) -> None:
        pen_border = QPen(self._fg_color)
        pen_border.setWidth(2)
        painter.setPen(pen_border)
        painter.drawEllipse(rect)

    def draw_sector(self, painter: QtGui.QPainter, my_rect: QtCore.QRect, value: float, max_value: float):
        hue_from = 0
        hue_to = 120
        pen_width = 2

        my_hue = int((hue_to - hue_from) * value / max_value + hue_from)
        my_color_pen = QtGui.QPen(self._fg_color)
        my_color_pen.setWidth(pen_width)
        my_color_brush = QtGui.QColor().fromHsl(my_hue, 255, 128)
        painter.setPen(my_color_pen)
        painter.setBrush(my_color_brush)
        painter.drawPie(my_rect,
                        int(5760 * (1.0 - value / max_value) + 1440),
                        int(5760 * value / max_value))

    def _paint_icon(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        pixmap = QPixmap(self._default_icon)
        painter.drawPixmap(rect, pixmap)

    def has_idle_display(self) -> bool:
        return False

    def has_next_display(self) -> bool:
        return False

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        if self.get_mode() not in ('working', 'resting'):
            painter.end()
            return

        margin = 0.05
        thickness = 0.3

        rw = rect.width()
        rh = rect.height()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        my_width = int(rw * (1 - 2 * margin) * thickness)
        my_height = int(rh * (1 - 2 * margin) * thickness)
        if self._team_value is not None:
            my_width /= 2
            my_height /= 2

        # My
        my_rect = QtCore.QRect(
            rect.left() + int(rw * margin),
            rect.top() + int(rh * margin),
            rect.width() - int(2 * rw * margin),
            rect.height() - int(2 * rh * margin),
        )

        if self._team_value is not None:
            # Team
            team_width = rw * (1 - 2 * margin) * thickness / 2
            team_height = rh * (1 - 2 * margin) * thickness / 2
        else:
            team_width = 0
            team_height = 0

        if thickness < 0.5 and not self._small:
            # Hole
            hole_rect = QtCore.QRect(
                my_rect.left() + my_width + team_width,
                my_rect.top() + my_height + team_height,
                my_rect.width() - 2 * (my_width + team_width),
                my_rect.height() - 2 * (my_height + team_height),
            )
            self.clear_pie(painter, hole_rect, rect)

        if self._my_max > 0:
            self.draw_sector(painter, my_rect, self._my_value, self._my_max)

        if self._team_value is not None:
            # Team
            team_rect = QtCore.QRect(
                my_rect.left() + my_width,
                my_rect.top() + my_height,
                my_rect.width() - 2 * my_width,
                my_rect.height() - 2 * my_height,
            )
            self.clear_pie(painter, team_rect, rect)
            if self._team_max > 0:
                self.draw_sector(painter, team_rect, self._team_value, self._team_max)

        if thickness < 0.5 and not self._small:
            # Draw the hole outline
            self.clear_pie_outline(painter, hole_rect, rect)

        painter.end()

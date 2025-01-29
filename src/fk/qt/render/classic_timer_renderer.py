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
from PySide6.QtGui import QColor, QPainterPath, QPen

from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer


class ClassicTimerRenderer(AbstractTimerRenderer):
    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None,
                 thin: bool = False,
                 small: bool = False):
        super(ClassicTimerRenderer, self).__init__(parent, bg_color, fg_color, thin, small)

    def clip(self, painter: QtGui.QPainter, rect: QtCore.QRectF | None, entire: QtCore.QRectF, shift: float = 0) -> None:
        # I also tried painter.setClipRegion(QRegion), but it won't apply antialiasing, looking ugly
        full = QPainterPath()
        full.addRect(entire)
        if rect is not None:
            hole = QPainterPath()
            hole.addEllipse(rect.center(), rect.width() / 2 + shift, rect.height() / 2 + shift)
            full = full.subtracted(hole)
        painter.setClipPath(full)

    def clear_pie_outline(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        pen_border = QPen(self._fg_color)
        pen_border.setWidthF(3)
        painter.setPen(pen_border)
        painter.drawEllipse(rect)

    def draw_sector(self, painter: QtGui.QPainter, my_rect: QtCore.QRectF, value: float, max_value: float):
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

    def has_idle_display(self) -> bool:
        return False

    def has_next_display(self) -> bool:
        return False

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        if self.get_mode() not in ('working', 'resting', 'tracking'):
            painter.end()
            return

        margin = 0.05
        thickness = 0.3
        has_two_sectors = self._team_value is not None or self._mode == 'tracking'

        rw = rect.width()
        rh = rect.height()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        my_width = rw * (1 - 2 * margin) * thickness
        my_height = rh * (1 - 2 * margin) * thickness
        if has_two_sectors:
            my_width /= 2
            my_height /= 2

        # My
        my_rect = QtCore.QRectF(
            rect.left() + rw * margin,
            rect.top() + rh * margin,
            rect.width() - 2 * rw * margin,
            rect.height() - 2 * rh * margin,
        )

        if has_two_sectors:
            # Team or tracking
            team_width = rw * (1 - 2 * margin) * thickness / 2
            team_height = rh * (1 - 2 * margin) * thickness / 2
        else:
            team_width = 0
            team_height = 0

        hole_rect = None
        if thickness < 0.5 and not self._small:
            # Hole
            hole_rect = QtCore.QRectF(
                my_rect.left() + my_width + team_width,
                my_rect.top() + my_height + team_height,
                my_rect.width() - 2 * (my_width + team_width),
                my_rect.height() - 2 * (my_height + team_height),
            )
            self.clip(painter, hole_rect, rect, 1)

        if has_two_sectors:
            # Team or tracking
            team_rect = QtCore.QRectF(
                my_rect.left() + my_width,
                my_rect.top() + my_height,
                my_rect.width() - 2 * my_width,
                my_rect.height() - 2 * my_height,
            )
            if self._team_value is not None and self._team_max > 0:
                self.draw_sector(painter, team_rect, self._team_value, self._team_max)
            elif self.get_mode() == 'tracking':
                hours = (self._my_value / 60 / 60) % 12
                self.draw_sector(painter, team_rect, hours, 12)
            self.clip(painter, team_rect, rect, 1)

        if self.get_mode() == 'tracking':
            minutes = (self._my_value / 60) % 60.0
            self.draw_sector(painter, my_rect, minutes, 60)
        elif self._my_max > 0:
            self.draw_sector(painter, my_rect, self._my_value, self._my_max)

        if hole_rect is not None:
            # Draw the hole outline
            self.clip(painter, hole_rect, rect, 0)
            self.clear_pie_outline(painter, hole_rect)

        painter.end()

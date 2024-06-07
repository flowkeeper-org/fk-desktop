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
from PySide6.QtGui import QColor, QPalette


class TimerRenderer(QtCore.QObject):
    _widget: QtWidgets.QWidget | None
    _bg_brush: QtGui.QBrush | QtGui.QColor | None
    _bg_pen: QtGui.QPen | QtGui.QColor | None
    _margin: float
    _thickness: float
    _my_value: float | None
    _is_set: bool
    _team_value: float | None
    _text: str
    _font: QtGui.QFont | None
    _font_color: QtGui.QColor | None
    _pen_width: int
    _hue_from: int
    _hue_to: int

    def __init__(self,
                 parent: QtWidgets.QWidget | None,
                 bg_pen: QtGui.QPen | QtGui.QColor | None,
                 bg_brush: QtGui.QBrush | QtGui.QColor | None,
                 margin: float,
                 thickness: float,
                 font: QtGui.QFont | None,
                 font_color: QtGui.QColor | None,
                 pen_width: int,
                 hue_from: int,
                 hue_to: int):
        super(TimerRenderer, self).__init__(parent)
        self._widget = parent
        self._bg_brush = bg_brush
        self._bg_pen = bg_pen
        self._margin = margin
        self._thickness = thickness
        self._font = font
        self._font_color = font_color
        self._pen_width = pen_width
        self._hue_from = hue_from
        self._hue_to = hue_to
        self.reset()

    def set_colors(self, fg_color: QColor, bg_color: QColor):
        self._bg_pen = fg_color
        self._bg_brush = bg_color
        self._font_color = fg_color

    def reset(self) -> None:
        self._my_value = 0
        self._team_value = None
        self._text = ""
        self._is_set = False

    def set_values(self, my: float | None, team: float | None = None, text: str = "") -> None:
        self._my_value = my
        self._team_value = team
        self._text = text
        self._is_set = True

    def clear_pie(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        painter.setPen(self._bg_pen)
        painter.setBrush(self._bg_brush)
        painter.drawEllipse(rect)

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect) -> None:
        if not self._is_set:
            painter.end()
            return

        rw = rect.width()
        rh = rect.height()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        my_width = int(rw * (1 - 2 * self._margin) * self._thickness)
        my_height = int(rh * (1 - 2 * self._margin) * self._thickness)
        if self._team_value is not None:
            my_width /= 2
            my_height /= 2

        # My
        my_rect = QtCore.QRect(
            rect.left() + int(rw * self._margin),
            rect.top() + int(rh * self._margin),
            rect.width() - int(2 * rw * self._margin),
            rect.height() - int(2 * rh * self._margin),
        )

        my_hue = int((self._hue_to - self._hue_from) * self._my_value + self._hue_from)
        if self._bg_pen is None:
            my_color_pen = QtGui.QPen(QtGui.QColor().fromHsl(my_hue, 255, 220))
        else:
            my_color_pen = QtGui.QPen(self._bg_pen)
        my_color_pen.setWidth(self._pen_width)
        my_color_brush = QtGui.QColor().fromHsl(my_hue, 255, 128)
        painter.setPen(my_color_pen)
        painter.setBrush(my_color_brush)
        painter.drawPie(my_rect, int(5760 * (1.0 - self._my_value) + 1440), int(5760 * self._my_value))

        if self._team_value is not None:
            # Team
            team_width = rw * (1 - 2 * self._margin) * self._thickness / 2
            team_height = rh * (1 - 2 * self._margin) * self._thickness / 2

            team_rect = QtCore.QRect(
                my_rect.left() + my_width,
                my_rect.top() + my_height,
                my_rect.width() - 2 * my_width,
                my_rect.height() - 2 * my_height,
            )
            self.clear_pie(painter, team_rect)

            team_hue = int((self._hue_to - self._hue_from) * self._team_value + self._hue_from)
            team_color_pen = QtGui.QPen(QtGui.QColor().fromHsl(team_hue, 255, 220))
            team_color_pen.setWidth(self._pen_width)
            team_color_brush = QtGui.QColor().fromHsl(team_hue, 255, 128)
            painter.setPen(team_color_pen)
            painter.setBrush(team_color_brush)
            painter.drawPie(team_rect, int(5760 * (1.0 - self._team_value) + 1440), int(5760 * self._team_value))
        else:
            team_width = 0
            team_height = 0

        if self._thickness < 0.5:
            # Hole
            hole_rect = QtCore.QRect(
                my_rect.left() + my_width + team_width,
                my_rect.top() + my_height + team_height,
                my_rect.width() - 2 * (my_width + team_width),
                my_rect.height() - 2 * (my_height + team_height),
            )
            self.clear_pie(painter, hole_rect)

        if self._text:
            painter.setPen(self._font_color)
            painter.setFont(self._font)
            painter.drawText(rect,
                             QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
                             self._text)

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

    def hide(self) -> None:
        if self._widget is None:
            raise Exception("Cannot hide a Pixmap")
        self._widget.hide()

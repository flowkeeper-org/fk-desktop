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
import logging

from PySide6.QtCore import QSize, Property, QEvent, Signal, QPoint
from PySide6.QtGui import QColor, QPalette, QMouseEvent
from PySide6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QToolButton

from fk.qt.render.classic_timer_renderer import ClassicTimerRenderer
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer

logger = logging.getLogger(__name__)


class TimerWidget(QWidget):
    _timer_display: MinimalTimerRenderer
    _fg_color: QColor
    _bg_color: QColor
    _last_values: dict | None

    clicked = Signal(QPoint)

    def __init__(self,
                 parent: QWidget,
                 name: str,
                 flavor: str,
                 center_button: QToolButton = None,
                 display_size: int = 63,
                 is_dark: bool = True):
        super().__init__(parent)
        self._last_values = None

        self.setObjectName(name)

        self._bg_color = self.palette().color(QPalette.ColorRole.Base)
        self._fg_color = self.palette().color(QPalette.ColorRole.Text)
        self._timer_display = None

        sp3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sp3.setHorizontalStretch(0)
        sp3.setVerticalStretch(0)
        self.setSizePolicy(sp3)
        self.setMinimumHeight(display_size)
        self.setMinimumWidth(display_size)
        self.setMaximumHeight(display_size)
        self.setMaximumWidth(display_size)
        self.setBaseSize(QSize(0, 0))

        inner_timer_layout = QHBoxLayout(self)
        inner_timer_layout.setObjectName(f"inner_{name}_layout")
        inner_timer_layout.setContentsMargins(0, 0, 0, 0)
        inner_timer_layout.setSpacing(0)

        if center_button is not None:
            inner_timer_layout.addWidget(center_button)

        self._init_renderer(flavor)

    def _init_renderer(self, flavor):
        if flavor == 'classic':
            cls = ClassicTimerRenderer
        elif flavor == 'minimal':
            cls = MinimalTimerRenderer

        if self._timer_display is not None:
            self.removeEventFilter(self._timer_display)
        self._timer_display = cls(self,
                                  self._bg_color,
                                  self._fg_color,
                                  True)
        self.installEventFilter(self._timer_display)
        self._timer_display.setObjectName('TimerWidgetRenderer')

    def _init_timer_display(self):
        if self._timer_display is not None:
            self._timer_display.set_colors(self._bg_color, self._fg_color)

    @Property('QColor')
    def fg_color(self):
        return self._fg_color

    @Property('QColor')
    def bg_color(self):
        return self._bg_color

    @fg_color.setter
    def fg_color(self, new_fg_color):
        if self._fg_color != new_fg_color:
            self._fg_color = new_fg_color
            self._init_timer_display()

    @bg_color.setter
    def bg_color(self, new_bg_color):
        if self._bg_color != new_bg_color:
            self._bg_color = new_bg_color
            self._init_timer_display()

    def reset(self):
        self._timer_display.reset()
        self._timer_display.repaint()

    def set_values(self,
                   my_value: float,
                   my_max: float,
                   team_value: float | None,
                   team_max: float | None,
                   mode: str) -> None:
        self._timer_display.set_values(my_value, my_max, team_value, team_max, mode)
        self._timer_display.repaint()
        self._last_values = {
            'my_value': my_value,
            'my_max': my_max,
            'team_value': team_value,
            'team_max': team_max,
            'mode': mode,
        }

    def get_last_values(self) -> dict():
        return self._last_values

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.type() == QEvent.Type.MouseButtonPress:
            self.clicked.emit(event.pos())

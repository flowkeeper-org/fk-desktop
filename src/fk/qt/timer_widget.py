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
from PySide6.QtGui import QFont, QColor, QPalette, QMouseEvent, Qt
from PySide6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QToolButton, QMenu, QApplication

from fk.qt.new_timer_renderer import NewTimerRenderer
from fk.qt.timer_renderer import TimerRenderer

logger = logging.getLogger(__name__)
DISPLAY_SIZE = 63


class TimerWidget(QWidget):
    _timer_display: NewTimerRenderer
    _fg_color: QColor
    _bg_color: QColor

    clicked = Signal(QPoint)

    def __init__(self,
                 parent: QWidget,
                 name: str,
                 flavor: str,
                 center_button: QToolButton = None):
        super().__init__(parent)
        self.setObjectName(name)

        self._bg_color = self.palette().color(QPalette.ColorRole.Base)
        self._fg_color = self.palette().color(QPalette.ColorRole.Text)

        sp3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sp3.setHorizontalStretch(0)
        sp3.setVerticalStretch(0)
        self.setSizePolicy(sp3)
        self.setMinimumHeight(DISPLAY_SIZE)
        self.setMinimumWidth(DISPLAY_SIZE)
        self.setMaximumHeight(DISPLAY_SIZE)
        self.setMaximumWidth(DISPLAY_SIZE)
        self.setBaseSize(QSize(0, 0))

        inner_timer_layout = QHBoxLayout(self)
        inner_timer_layout.setObjectName(f"inner_{name}_layout")
        inner_timer_layout.setContentsMargins(0, 0, 0, 0)
        inner_timer_layout.setSpacing(0)

        if center_button is not None:
            inner_timer_layout.addWidget(center_button)

        if flavor == 'classic':
            cls = TimerRenderer
        elif flavor == 'minimal':
            cls = NewTimerRenderer

        self._timer_display = cls(
            self,
            self._fg_color,
            self._bg_color,
            0.05,
            0.3,
            QFont(),
            self._fg_color,
            2,
            0,
            120)
        self.installEventFilter(self._timer_display)

    def _init_timer_display(self):
        self._timer_display.set_colors(self._fg_color, self._bg_color)
        self._timer_display.repaint()

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

    def set_values(self, completion, is_work) -> None:
        self._timer_display.set_values(completion, is_work=is_work)
        self._timer_display.repaint()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.type() == QEvent.Type.MouseButtonPress:
            self.clicked.emit(event.pos())

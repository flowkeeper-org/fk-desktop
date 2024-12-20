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
from abc import abstractmethod
from typing import Self

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject, QRect
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget


logger = logging.getLogger(__name__)


class AbstractTimerRenderer(QObject):
    _widget: QWidget | None
    _my_value: float | None
    _my_max: float | None
    _team_value: float | None
    _team_max: float | None
    _mode: str
    _bg_color: QColor
    _fg_color: QColor

    def __init__(self,
                 parent: QWidget | None,
                 bg_color: QColor = None,
                 fg_color: QColor = None) -> Self:
        super(AbstractTimerRenderer, self).__init__(parent)
        self._widget = parent
        if bg_color is None or fg_color is None:
            raise Exception('Renderer needs to know the colors')
        self._bg_color = bg_color
        self._fg_color = fg_color
        self.reset()

    def set_colors(self, bg_color: QColor, fg_color: QColor):
        self._bg_color = bg_color
        self._fg_color = fg_color
        self.repaint()

    def reset(self) -> None:
        self._my_value = 0
        self._my_max = 0
        self._team_value = None
        self._team_max = None
        self._mode = 'idle'

    def set_values(self,
                   my_value: float,
                   my_max: float,
                   team_value: float | None,
                   team_max: float | None,
                   mode: str) -> None:
        self._my_value = my_value
        self._my_max = my_max
        self._team_value = team_value
        self._team_max = team_max
        self._mode = mode

    @abstractmethod
    def paint(self, painter: QPainter, rect: QRect) -> None:
        pass

    def eventFilter(self, widget: QtWidgets.QWidget, event: QtCore.QEvent) -> bool:
        if self._widget is None:
            logger.error(f"Cannot filter events like {event} on a {self.__class__.__name__}")
        if widget == self._widget and event.type() == QtCore.QEvent.Type.Paint:
            painter = QtGui.QPainter(widget)
            rect = widget.contentsRect()
            self.paint(painter, rect)
            return True
        return False

    def repaint(self, painter: QPainter = None, rect: QRect = None) -> None:
        if self._widget is None:
            self.paint(painter, rect)
        else:
            self._widget.repaint()

    def get_mode(self):
        return self._mode

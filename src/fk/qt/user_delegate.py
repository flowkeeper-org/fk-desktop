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
import random

from PySide6 import QtWidgets, QtCore, QtSvg, QtGui
from PySide6.QtCore import QSize, Qt, QRect, QPoint
from PySide6.QtGui import QPen, QBrush, QColor


class UserDelegate(QtWidgets.QItemDelegate):
    _theme: str
    _text_color: str

    def _get_renderer(self, name):
        return QtSvg.QSvgRenderer(f':/icons/{self._theme}/24x24/pomodoro-{name}.svg')

    def __init__(self, parent: QtCore.QObject = None, theme: str = 'mixed', text_color: str = '#000'):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._text_color = text_color

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        painter.save()
        painter.translate(option.rect.topLeft())

        bar_height = 4
        height = option.rect.height()
        width = option.rect.width()

        painter.drawText(QRect(0, 4, width, height),
                         Qt.AlignmentFlag.AlignLeft,
                         index.data())

        # TODO: Get this from data
        max_duration = 30 * 60
        work_duration = 25 * 60
        current_duration = random.randint(1, 31) * 60

        bar_top = height - bar_height - 6
        bar_bottom = height - 6

        painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QBrush(QColor('#EE4B2B')))
        painter.drawRect(0, bar_top, width - 1 - 100, bar_height)

        painter.setBrush(QBrush(QColor('#AAFF00')))
        painter.drawRect(width - 1 - 100, bar_top, 100, bar_height)

        x = 45
        painter.setBrush(QBrush(QColor(self._text_color)))
        painter.drawPolygon([QPoint(x, bar_bottom + 1), QPoint(x + 4, height - 1), QPoint(x - 4, height - 1)])

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(size.height() + 6)
        return size

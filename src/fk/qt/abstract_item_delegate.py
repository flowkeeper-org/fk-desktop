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

from PySide6.QtCore import QObject
from PySide6.QtGui import Qt, QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QStyleOptionViewItem, QItemDelegate, QStyle


class AbstractItemDelegate(QItemDelegate):
    _selection_brush: QBrush
    _crossout_pen: QPen
    _theme: str
    _padding: float

    def __init__(self,
                 parent: QObject = None,
                 theme: str = 'mixed',
                 selection_color: str = '#555',
                 crossout_color: str = '#777',
                 padding: float = 4):
        QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._padding = padding
        self._selection_brush = QBrush(QColor(selection_color), Qt.BrushStyle.SolidPattern)
        self._crossout_pen = QPen(QColor(crossout_color))

    def paint_background(self, painter: QPainter, option: QStyleOptionViewItem, is_sealed: bool):
        painter.save()

        if QStyle.StateFlag.State_Selected in option.state:
            painter.fillRect(option.rect, self._selection_brush)

        if is_sealed:
            painter.setPen(self._crossout_pen)
            painter.translate(option.rect.topLeft())
            lh = option.fontMetrics.height()
            lines = int(option.rect.height() / lh)
            for i in range(lines):
                painter.drawLine(0,
                                 lh * (i + 0.5) + self._padding,
                                 option.rect.width(),
                                 lh * (i + 0.5) + self._padding)

        painter.restore()

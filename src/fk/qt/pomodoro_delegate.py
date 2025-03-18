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
import datetime

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import QSize, QPoint, QRect
from PySide6.QtGui import Qt, QBrush, QColor

POMODORO_VOIDED = "voided"

POMODORO_NEW_PLANNED = "new-planned"
POMODORO_FINISHED_PLANNED = "finished-planned"
POMODORO_RUNNING_PLANNED = "running-planned"

POMODORO_NEW_UNPLANNED = "new-unplanned"
POMODORO_FINISHED_UNPLANNED = "finished-unplanned"
POMODORO_RUNNING_UNPLANNED = "running-unplanned"


class PomodoroDelegate(QtWidgets.QItemDelegate):
    _selection_brush: QBrush
    _theme: str

    def __init__(self,
                 parent: QtCore.QObject = None,
                 theme: str = 'mixed',
                 selection_color: str = '#555'):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._selection_brush = QBrush(QColor(selection_color), Qt.BrushStyle.SolidPattern)

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        if index.data(501) == 'pomodoro':  # We can also get a drop placeholder here, which we don't want to paint
            painter.save()
            space: QtCore.QRectF = option.rect

            # Qt 6.8 forced delegates to paint their backgrounds themselves
            if QtWidgets.QStyle.StateFlag.State_Selected in option.state:
                painter.fillRect(space, self._selection_brush)

            s: QSize = index.data(Qt.ItemDataRole.SizeHintRole)
            height = s.height()
            left = space.left()

            workitem = index.data(500)
            if workitem.is_tracker():
                elapsed: str = index.data()
                rect = QtCore.QRectF(
                    left + 4,
                    space.top() + 4,
                    space.width() - 4,
                    height - 4)
                painter.drawText(rect, elapsed)
            else:
                for p in workitem.values():
                    width = height
                    rect = QtCore.QRectF(
                        left,
                        space.top(),  # space.center().y() - (size / 2) + 1,
                        width,
                        height)

                    if p.is_running():
                        renderer = POMODORO_RUNNING_PLANNED if p.is_planned() else POMODORO_RUNNING_UNPLANNED
                    elif p.is_finished():
                        renderer = POMODORO_FINISHED_PLANNED if p.is_planned() else POMODORO_FINISHED_UNPLANNED
                    else:
                        renderer = POMODORO_NEW_PLANNED if p.is_planned() else POMODORO_NEW_UNPLANNED

                    left += width

                    for _ in range(len(p)):
                        width = height / 4
                        rect = QtCore.QRectF(
                            left,
                            space.top(),  # space.center().y() - (size / 2) + 1,
                            width,
                            height)

                        left += width

            painter.restore()

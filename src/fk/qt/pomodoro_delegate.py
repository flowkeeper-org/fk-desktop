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

from PySide6 import QtWidgets, QtCore, QtSvg, QtGui


class PomodoroDelegate(QtWidgets.QItemDelegate):
    _svg_renderer: dict[str, QtSvg.QSvgRenderer]

    @staticmethod
    def _get_renderer(name):
        return QtSvg.QSvgRenderer(f':/icons/pomodoro-{name}.svg')

    def __init__(self, parent: QtCore.QObject = None):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._svg_renderer = {
            '[x]': PomodoroDelegate._get_renderer('[x]'),
            '[ ]': PomodoroDelegate._get_renderer("[ ]"),
            '[v]': PomodoroDelegate._get_renderer("[v]"),
            '[#]': PomodoroDelegate._get_renderer("[#]"),
            '(x)': PomodoroDelegate._get_renderer("(x)"),
            '( )': PomodoroDelegate._get_renderer("( )"),
            '(v)': PomodoroDelegate._get_renderer("(v)"),
            '(#)': PomodoroDelegate._get_renderer("(#)"),
        }

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        size = option.rect.height()
        for i, p in enumerate(index.data().split(',')):
            if p != '':
                rect = QtCore.QRect(
                    option.rect.left() + size * i,
                    option.rect.center().y() - (size / 2) + 1,
                    size,
                    size)
                self._svg_renderer[p].render(painter, rect)

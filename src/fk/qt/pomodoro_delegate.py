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
from PySide6.QtCore import QSize
from PySide6.QtGui import Qt


class PomodoroDelegate(QtWidgets.QItemDelegate):
    _svg_renderer: dict[str, QtSvg.QSvgRenderer]
    _theme: str

    def _get_renderer(self, name):
        return QtSvg.QSvgRenderer(f':/icons/{self._theme}/24x24/pomodoro-{name}.svg')

    def __init__(self, parent: QtCore.QObject = None, theme: str = 'mixed'):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._svg_renderer = {
            '[x]': self._get_renderer('[x]'),
            '[ ]': self._get_renderer("[ ]"),
            '[v]': self._get_renderer("[v]"),
            '[#]': self._get_renderer("[#]"),
            '(x)': self._get_renderer("(x)"),
            '( )': self._get_renderer("( )"),
            '(v)': self._get_renderer("(v)"),
            '(#)': self._get_renderer("(#)"),
        }

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        if index.data(501) == 'pomodoro':  # We can also get a drop placeholder here, which we don't want to paint
            s: QSize = index.data(Qt.ItemDataRole.SizeHintRole)
            height = s.height()
            left = option.rect.left()
            for i, p in enumerate(index.data().split(',')):
                if p != '':
                    width = height if p != '[x]' and p != '(x)' else height / 4
                    rect = QtCore.QRect(
                        left,
                        option.rect.top(),  # option.rect.center().y() - (size / 2) + 1,
                        width,
                        height)
                    self._svg_renderer[p].render(painter, rect)
                    left += width

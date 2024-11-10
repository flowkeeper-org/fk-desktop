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
import re
from html import escape

from PySide6 import QtWidgets, QtCore, QtSvg, QtGui
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QTextDocument

from fk.core.workitem import Workitem

TAG_REGEX = re.compile('#(\\w+)')


class WorkitemTextDelegate(QtWidgets.QItemDelegate):
    _theme: str
    _text_color: str

    def _get_renderer(self, name):
        return QtSvg.QSvgRenderer(f':/icons/{self._theme}/24x24/pomodoro-{name}.svg')

    def __init__(self, parent: QtCore.QObject = None, theme: str = 'mixed', text_color: str = '#000'):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._text_color = text_color

    def _format_html(self, workitem: Workitem) -> str:
        text = workitem.get_name()
        text = TAG_REGEX.sub('<b>\\1</b>', escape(text, False))
        return (f'<span '
                f'style="color: {self._text_color}; '
                f'text-decoration: {"line-through" if workitem.is_sealed() else "none"}; '
                f'font-weight: {"bold" if workitem.is_running() else "normal"};">'
                f'{text}'
                f'</span>')

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        painter.save()
        painter.translate(option.rect.topLeft())

        document = QTextDocument(self)
        document.setTextWidth(option.rect.width())

        workitem: Workitem = index.data(500)
        document.setHtml(self._format_html(workitem))
        document.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(size.height() + 6)
        return size

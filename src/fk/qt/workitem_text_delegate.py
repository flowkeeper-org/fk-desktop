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

from PySide6 import QtWidgets, QtCore, QtSvg, QtGui
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QTextDocument


TAG_REGEX = re.compile('#(\\w+)')
DATE_REGEX = re.compile('([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])')


class WorkitemTextDelegate(QtWidgets.QItemDelegate):
    _theme: str
    _text_color: str

    def _get_renderer(self, name):
        return QtSvg.QSvgRenderer(f':/icons/{self._theme}/24x24/pomodoro-{name}.svg')

    def __init__(self, parent: QtCore.QObject = None, theme: str = 'mixed', text_color: str = '#000'):
        QtWidgets.QItemDelegate.__init__(self, parent)
        self._theme = theme
        self._text_color = text_color

    def _format_html(self, s: str) -> str:
        s = TAG_REGEX.sub('<b>\\1</b>', s)
        s = DATE_REGEX.sub('<b>\\1</b>', s)
        return f'<span style="color: {self._text_color};">{s}</span>'

    def _format_html_old(self, s: str) -> str:
        s = TAG_REGEX.sub('<span style="background-color: #999; color: #fff;">&nbsp;\\1&nbsp;</span>', s)
        s = DATE_REGEX.sub('<span style="background-color: #77F; color: #fff;">&nbsp;\\1&nbsp;</span>', s)
        return f'<span style="color: {self._text_color};">{s}</span>'

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        painter.save()
        painter.translate(option.rect.topLeft())

        # painter.drawText(QRect(0, 4, option.rect.width(), option.rect.height()),
        #                  Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        #                  index.data())
        document = QTextDocument(self)
        document.setTextWidth(option.rect.width())
        document.setHtml(self._format_html(index.data()))
        # document.setPlainText(index.data())
        document.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(size.height() + 6)
        return size

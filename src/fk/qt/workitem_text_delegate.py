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

from PySide6.QtCore import QSize, QObject, QModelIndex
from PySide6.QtGui import QStaticText, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem

from fk.core.workitem import Workitem
from fk.qt.abstract_item_delegate import AbstractItemDelegate

TAG_REGEX = re.compile('#(\\w+)')


class WorkitemTextDelegate(AbstractItemDelegate):
    _text_color: str

    def __init__(self,
                 parent: QObject = None,
                 theme: str = 'mixed',
                 text_color: str = '#000',
                 selection_color: str = '#555',
                 crossout_color: str = '#777',
                 padding: float = 4):
        AbstractItemDelegate.__init__(self, parent, theme, selection_color, crossout_color, padding)
        self._text_color = text_color

    def _format_html(self, workitem: Workitem, is_placeholder: bool) -> str:
        text = workitem.get_name()
        text = TAG_REGEX.sub('<b>\\1</b>', escape(text, False))
        return (f'<span '
                f'style="color: {"gray" if is_placeholder else self._text_color}; '
                f'text-decoration: {"line-through" if workitem.is_sealed() else "none"}; '
                # f'font-weight: {"bold" if workitem.is_running() else "normal"};'
                f'">{text}</span>')

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        is_placeholder = index.data(501) == 'drop'
        painter.save()

        workitem: Workitem = index.data(500)
        self.paint_background(painter, option, workitem.is_sealed())

        st = QStaticText(self._format_html(workitem, is_placeholder))
        st.setTextWidth(option.rect.width())

        painter.translate(option.rect.topLeft())
        painter.drawStaticText(0, 4, st)

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        size.setHeight(size.height() + 6)
        return size

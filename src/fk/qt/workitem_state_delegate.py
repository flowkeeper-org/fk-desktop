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

from PySide6.QtCore import QModelIndex, QObject
from PySide6.QtGui import Qt, QPainter, QStaticText
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QStyleOptionViewItem

from fk.qt.abstract_item_delegate import AbstractItemDelegate, get_padding


class WorkitemStateDelegate(AbstractItemDelegate):
    _svg_renderer: QSvgRenderer
    _text_color: str

    def __init__(self,
                 parent: QObject = None,
                 theme: str = 'mixed',
                 text_color: str = '#000',
                 selection_color: str = '#555',
                 crossout_color: str = '#777'):
        AbstractItemDelegate.__init__(self, parent, theme, selection_color, crossout_color)
        self._svg_renderer = QSvgRenderer(
            f':/icons/{self._theme}/24x24/workitem-unplanned.svg',
            aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        self._text_color = text_color

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if index.data(501) == 'planned':  # We can also get a drop placeholder here, which we don't want to paint
            painter.save()

            workitem = index.data(500)
            self.paint_background(painter, option, workitem.is_sealed())

            if not workitem.is_planned():
                padding = get_padding(option)
                rect = option.rect.adjusted(-2, padding, -2, -padding)
                rect.setHeight(option.fontMetrics.height())
                self._svg_renderer.render(painter, rect)

            painter.restore()
        elif index.data(501) == 'category':
            painter.save()

            txt = index.data(503)
            # If you uncomment this, the text in parentheses will be light and gray. But the columns won't resize
            # correctly anymore, as Qt treats all text as bold when it computes its width.
            # txt = txt.replace('(', '</strong><span style="color: gray;">(').replace(')', ')</span><strong>')
            st = QStaticText(f'<span style="color: {self._text_color};"><strong>{txt}</strong></span>')
            st.setTextOption(Qt.AlignmentFlag.AlignLeft)
            st.setTextWidth(option.rect.width())
            painter.drawStaticText(option.rect.left(),
                                   option.rect.top() + get_padding(option),
                                   st)

            painter.restore()

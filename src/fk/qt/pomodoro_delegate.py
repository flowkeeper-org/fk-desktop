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

from PySide6.QtCore import QSize, QObject, QRectF, QModelIndex
from PySide6.QtGui import Qt, QBrush, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QStyleOptionViewItem

from fk.core.workitem import Workitem
from fk.qt.abstract_item_delegate import AbstractItemDelegate

POMODORO_VOIDED = "voided"

POMODORO_NEW_PLANNED = "new-planned"
POMODORO_FINISHED_PLANNED = "finished-planned"
POMODORO_RUNNING_PLANNED = "running-planned"

POMODORO_NEW_UNPLANNED = "new-unplanned"
POMODORO_FINISHED_UNPLANNED = "finished-unplanned"
POMODORO_RUNNING_UNPLANNED = "running-unplanned"


class PomodoroDelegate(AbstractItemDelegate):
    _svg_renderer: dict[str, QSvgRenderer]
    _selection_brush: QBrush
    _theme: str
    _cross_out: bool
    _display_tags: bool

    def _get_renderer(self, name):
        return QSvgRenderer(
            f':/icons/{self._theme}/24x24/pomodoro-{name}.svg',
            aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

    def __init__(self,
                 parent: QObject = None,
                 theme: str = 'mixed',
                 selection_color: str = '#555',
                 crossout_color: str = '#777',
                 padding: float = 4,
                 display_tags: bool = False):
        AbstractItemDelegate.__init__(self, parent, theme, selection_color, crossout_color, padding)
        self._display_tags = display_tags
        self._svg_renderer = {
            POMODORO_VOIDED: self._get_renderer(POMODORO_VOIDED),
            POMODORO_NEW_PLANNED: self._get_renderer(POMODORO_NEW_PLANNED),
            POMODORO_FINISHED_PLANNED: self._get_renderer(POMODORO_FINISHED_PLANNED),
            POMODORO_RUNNING_PLANNED: self._get_renderer(POMODORO_RUNNING_PLANNED),
            POMODORO_NEW_UNPLANNED: self._get_renderer(POMODORO_NEW_UNPLANNED),
            POMODORO_FINISHED_UNPLANNED: self._get_renderer(POMODORO_FINISHED_UNPLANNED),
            POMODORO_RUNNING_UNPLANNED: self._get_renderer(POMODORO_RUNNING_UNPLANNED),
        }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if index.data(501) == 'pomodoro':  # We can also get a drop placeholder here, which we don't want to paint
            painter.save()
            space: QRectF = option.rect

            workitem: Workitem = index.data(500)
            self.paint_background(painter, option, workitem.is_sealed() if self._display_tags else False)

            s: QSize = index.data(Qt.ItemDataRole.SizeHintRole)
            height = s.height()
            left = space.left()

            if workitem.is_tracker():
                elapsed: str = index.data()
                rect = QRectF(
                    left + 4,
                    space.top() + 4,
                    space.width() - 4,
                    height - 4)
                painter.drawText(rect, elapsed)
            else:
                for p in workitem.values():
                    width = height
                    rect = QRectF(
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

                    self._svg_renderer[renderer].render(painter, rect)
                    left += width

                    for _ in range(len(p)):
                        width = height / 4
                        rect = QRectF(
                            left,
                            space.top(),  # space.center().y() - (size / 2) + 1,
                            width,
                            height)

                        self._svg_renderer[POMODORO_VOIDED].render(painter, rect)
                        left += width

            painter.restore()

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
import logging

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget, QAbstractItemView

from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.workitem_tableview import WorkitemTableView

logger = logging.getLogger(__name__)


def _get_row_position(widget: QAbstractItemView, row: int, col: int = 0) -> QPoint:
    row_rect = widget.visualRect(widget.model().index(row, col))
    return QPoint(row_rect.center().x() * 0.5, row_rect.bottomRight().y() + 10)


def get_tutorial_step(step: int, main_window: QWidget) -> (str, QPoint, str):
    logger.debug(f'Tutorial step {step}')
    if step == 1:
        backlogs: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        return '1 / 10: Backlogs are To Do lists. You would usually start your day by creating a new backlog.', \
            backlogs.parentWidget().mapToGlobal(backlogs.rect().center()), 'info'

    elif step == 2:
        backlogs: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")

        pos = _get_row_position(backlogs, 1)
        # return '1 / 10: Backlogs are To Do lists. You would usually start your day by creating a new backlog. ' \
        #        'You can create project backlogs, long-term to-do lists, etc.', \
        #     backlogs.mapToGlobal(pos)
        return '1 / 10: Backlogs are To Do lists.', backlogs.parentWidget().mapToGlobal(pos), 'arrow'
        # backlogs.parentWidget().mapToGlobal(backlogs.rect().center())
    elif step == 3:
        workitems: WorkitemTableView = main_window.findChild(WorkitemTableView, "workitems_table")
        return '2 / 10: Work items', workitems.parentWidget().mapToGlobal(workitems.rect().center()), 'info'
    elif step == 4:
        return '3 / 10: Thank you!', main_window.mapToGlobal(main_window.rect().center()), 'info'


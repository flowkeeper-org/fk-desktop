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
from __future__ import annotations

import datetime
import logging

from PySide6 import QtGui, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_timer import AbstractTimer
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import RenameBacklogStrategy, ReorderBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import MoveWorkitemStrategy
from fk.qt.abstract_drop_model import AbstractDropModel
from fk.qt.qt_timer import QtTimer

logger = logging.getLogger(__name__)
font_new = QtGui.QFont()
font_today = QtGui.QFont()
# font_today.setBold(True)


class BacklogItem(QStandardItem):
    _backlog: Backlog

    def __init__(self, backlog: Backlog):
        super().__init__()
        self._backlog = backlog
        self.setData(backlog, 500)
        self.setData(backlog.get_name(), Qt.ItemDataRole.ToolTipRole)
        self.setData('title', 501)
        default_flags = (Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsDragEnabled |
                         Qt.ItemFlag.ItemIsDropEnabled |    # For workitems
                         Qt.ItemFlag.ItemIsEditable)
        self.setFlags(default_flags)
        self.update_display()
        self.update_font()

    def update_display(self):
        self.setData(self._backlog.get_name(), Qt.ItemDataRole.DisplayRole)

    def update_font(self):
        font = font_today if self._backlog.is_today() else font_new
        self.setData(font, Qt.ItemDataRole.FontRole)

    def __lt__(self, other: BacklogItem):
        return self._backlog.get_last_modified_date() < other._backlog.get_last_modified_date()


class BacklogModel(AbstractDropModel):
    _midnight_timer: AbstractTimer

    def __init__(self,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(1, parent, source_holder)
        self._midnight_timer = QtTimer('Midnight check for BacklogModel')
        self._schedule_at_midnight()
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.itemChanged.connect(lambda item: self.handle_rename(item, RenameBacklogStrategy))

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.load(None)
        source.on(events.AfterBacklogCreate, self._backlog_added)
        source.on(events.AfterBacklogDelete, self._backlog_removed)
        source.on(events.AfterBacklogRename, self._backlog_renamed)
        source.on(events.AfterBacklogReorder, self._backlog_reordered)

    def _backlog_added(self, backlog: Backlog, **kwargs) -> None:
        self.insertRow(0, BacklogItem(backlog))

    def _backlog_removed(self, backlog: Backlog, **kwargs) -> None:
        for i in range(self.rowCount()):
            bl = self.item(i).data(500)
            if bl == backlog:
                self.removeRow(i)
                return

    def _backlog_renamed(self, backlog: Backlog, **kwargs) -> None:
        for i in range(self.rowCount()):
            bl = self.item(i).data(500)
            if bl == backlog:
                self.item(i).update_display()
                return

    def _schedule_at_midnight(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        diff: datetime.timedelta = datetime.datetime(year=tomorrow.year,
                                                     month=tomorrow.month,
                                                     day=tomorrow.day) - datetime.datetime.now()
        wait_for = (int(diff.total_seconds()) + 60) * 1000
        logger.debug(f'Scheduled _at_midnight in {wait_for}ms')
        self._midnight_timer.schedule(wait_for, self._at_midnight, None, True)

    def _at_midnight(self, params: dict | None, when: datetime.datetime | None = None) -> None:
        logger.debug(f'Fired _at_midnight at {datetime.datetime.now()}')
        for i in range(self.rowCount()):
            self.item(i).update_font()
        self._schedule_at_midnight()    # Reschedule

    def _backlog_reordered(self, backlog: Backlog, new_index: int, carry: str, **kwargs) -> None:
        if carry != 'ui':
            for old_index in range(self.rowCount()):
                bl = self.item(old_index).data(500)
                if bl == backlog:
                    new_index = self.rowCount() - new_index
                    if new_index > old_index:
                        new_index -= 1
                    row = self.takeRow(old_index)
                    self.insertRow(new_index, row)
                    return

    def load(self, user: User | None) -> None:
        self.clear()
        if user is not None:
            for backlog in reversed(user.values()):
                self.appendRow(BacklogItem(backlog))
        self.setHorizontalHeaderItem(0, QStandardItem(''))

    def get_primary_type(self) -> str:
        return 'application/flowkeeper.backlog.id'

    def get_secondary_type(self) -> str:
        return 'application/flowkeeper.workitem.id'

    def item_for_object(self, backlog: Backlog) -> list[QStandardItem]:
        return [BacklogItem(backlog)]
    
    def reorder(self, to_index: int, uid: str):
        self._source_holder.get_source().execute(ReorderBacklogStrategy,
                                                 # We display backlogs in reverse order, so need to subtract here
                                                 [uid, str(self.rowCount() - to_index)],
                                                 carry='ui')

    def adopt_foreign_item(self, backlog: Backlog, workitem_uid: str) -> bool:
        workitem: Workitem = self._source_holder.get_source().find_workitem(workitem_uid)
        if workitem is None or backlog is None or workitem.get_parent() == backlog:
            return False
        logger.debug(f'Moving workitem {workitem.get_name()} to backlog {backlog.get_name()}')
        self._source_holder.get_source().execute(MoveWorkitemStrategy,
                                                 [workitem_uid, backlog.get_uid()])
        return True

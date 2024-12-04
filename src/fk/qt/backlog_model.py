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

import logging

from PySide6 import QtGui, QtWidgets, QtCore
from PySide6.QtCore import Qt

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import RenameBacklogStrategy, ReorderBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.user import User
from fk.qt.abstract_drop_model import AbstractDropModel

logger = logging.getLogger(__name__)
font_new = QtGui.QFont()
font_today = QtGui.QFont()
font_today.setBold(True)


class BacklogItem(QtGui.QStandardItem):
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
    def __init__(self,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(1, parent, source_holder)
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.itemChanged.connect(lambda item: self._handle_rename(item))

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.load(None)
        source.on(events.AfterBacklogCreate, self._backlog_added)
        source.on(events.AfterBacklogDelete, self._backlog_removed)
        source.on(events.AfterBacklogRename, self._backlog_renamed)

    def _handle_rename(self, item: QtGui.QStandardItem) -> None:
        if item.data(501) == 'title':
            backlog = item.data(500)
            old_name = backlog.get_name()
            new_name = item.text()
            if old_name != new_name:
                try:
                    self._source_holder.get_source().execute(RenameBacklogStrategy, [backlog.get_uid(), new_name])
                except Exception as e:
                    logger.error(f'Failed to rename {old_name} to {new_name}', exc_info=e)
                    item.setText(old_name)
                    QtWidgets.QMessageBox().warning(
                        self.parent(),
                        "Cannot rename",
                        str(e),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

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

    def load(self, user: User) -> None:
        self.clear()
        if user is not None:
            for backlog in reversed(user.values()):
                self.appendRow(BacklogItem(backlog))
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))

    def get_type(self) -> str:
        return 'application/flowkeeper.backlog.id'

    def item_by_id(self, uid: str) -> BacklogItem:
        return BacklogItem(self._source_holder.get_source().find_backlog(uid))

    def reorder(self, to_index: int, uid: str):
        self._source_holder.get_source().execute(ReorderBacklogStrategy,
                                                 # We display backlogs in reverse order, so need to subtract here
                                                 [uid, str(self.rowCount() - to_index - 1)])

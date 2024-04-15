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

from typing import Self

from PySide6 import QtGui, QtWidgets, QtCore
from PySide6.QtCore import Qt

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import RenameBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.user import User

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
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
        self.update_display()
        self.update_font()

    def update_display(self):
        self.setData(self._backlog.get_name(), Qt.DisplayRole)

    def update_font(self):
        font = font_today if self._backlog.is_today() else font_new
        self.setData(font, Qt.FontRole)

    def __lt__(self, other: Self):
        return self._backlog.get_last_modified_date() < other._backlog.get_last_modified_date()


class BacklogModel(QtGui.QStandardItemModel):
    _source_holder: EventSourceHolder
    _user: User | None

    def __init__(self,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(0, 1, parent)
        self._source_holder = source_holder
        self._user = None
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self._on_source_changed("", source_holder.get_source())
        self.itemChanged.connect(lambda item: self._handle_rename(item))

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.load(None)
        source.on(events.AfterBacklogCreate, self._backlog_added)
        source.on(events.AfterBacklogDelete, self._backlog_removed)
        source.on(events.AfterBacklogRename, self._backlog_renamed)
        source.on('*', self._sort)

    def _handle_rename(self, item: QtGui.QStandardItem) -> None:
        if item.data(501) == 'title':
            backlog = item.data(500)
            old_name = backlog.get_name()
            new_name = item.text()
            if old_name != new_name:
                try:
                    self._source_holder.get_source().execute(RenameBacklogStrategy, [backlog.get_uid(), new_name])
                except Exception as e:
                    item.setText(old_name)
                    QtWidgets.QMessageBox().warning(
                        self.parent(),
                        "Cannot rename",
                        str(e),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

    def _backlog_added(self, backlog: Backlog, **kwargs) -> None:
        self.appendRow(BacklogItem(backlog))

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
        self._user = user
        if user is not None:
            for backlog in user.values():
                self.appendRow(BacklogItem(backlog))
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))
        self._sort()

    def _sort(self, event: str = None, **kwargs):
        self.sort(0, Qt.SortOrder.DescendingOrder)

    def get_user(self) -> User | None:
        return self._user

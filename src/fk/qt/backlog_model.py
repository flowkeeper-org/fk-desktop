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

font_new = QtGui.QFont()
font_today = QtGui.QFont()
font_today.setBold(True)


class BacklogItem(QtGui.QStandardItem):
    _backlog: Backlog

    def __init__(self, backlog: Backlog):
        super().__init__()
        self._backlog = backlog
        self.setData(backlog, 500)
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
    _source: AbstractEventSource
    _username: str

    def __init__(self, parent: QtCore.QObject, source: AbstractEventSource, username: str):
        super().__init__(0, 1, parent)
        self._source = source
        self._username = username
        source.connect(events.AfterBacklogCreate, self._backlog_added)
        source.connect(events.AfterBacklogDelete, self._backlog_removed)
        source.connect(events.AfterBacklogRename, self._backlog_renamed)
        source.connect('*', self.on_update)
        self.itemChanged.connect(lambda item: self._handle_rename(item))

    def _handle_rename(self, item: QtGui.QStandardItem) -> None:
        if item.data(501) == 'title':
            backlog = item.data(500)
            old_name = backlog.get_name()
            new_name = item.text()
            if old_name != new_name:
                try:
                    self._source.execute(RenameBacklogStrategy, [backlog.get_uid(), new_name])
                except Exception as e:
                    item.setText(old_name)
                    QtWidgets.QMessageBox().warning(
                        self.parent(),
                        "Cannot rename",
                        str(e),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

    def _backlog_added(self, event: str, backlog: Backlog) -> None:
        self.appendRow(BacklogItem(backlog))

    def _backlog_removed(self, event: str, backlog: Backlog) -> None:
        for i in range(self.rowCount()):
            bl = self.item(i).data(500)
            if bl == backlog:
                self.removeRow(i)
                return

    def _backlog_renamed(self, event: str, backlog: Backlog, old_name: str, new_name: str) -> None:
        for i in range(self.rowCount()):
            bl = self.item(i).data(500)
            if bl == backlog:
                self.item(i).update_display()
                return

    def load(self) -> None:
        self.clear()
        for backlog in self._source.get_data().get(self._username).values():
            self.appendRow(BacklogItem(backlog))
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))
        self.on_update()

    def on_update(self, event: str = None, **kwargs):
        self.sort(0, Qt.SortOrder.DescendingOrder)

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

from PySide6 import QtGui, QtCore
from PySide6.QtCore import Qt

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.tenant import Tenant
from fk.core.user import User


class UserModel(QtGui.QStandardItemModel):
    _font_normal: QtGui.QFont
    _font_busy: QtGui.QFont

    def __init__(self, parent: QtCore.QObject, source_holder: EventSourceHolder):
        super().__init__(0, 1, parent)
        self._font_normal = QtGui.QFont()
        self._font_busy = QtGui.QFont()
        self._font_busy.setBold(True)
        source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        source.on(events.AfterUserCreate, self._user_added)
        source.on(events.AfterUserDelete, self._user_removed)
        source.on(events.AfterUserRename, self._user_renamed)

    def _user_added(self, event: str, user: User) -> None:
        item = QtGui.QStandardItem('')
        self.appendRow(item)
        self.set_row(self.rowCount() - 1, user)

    def _user_removed(self, event: str, user: User) -> None:
        for i in range(self.rowCount()):
            u = self.item(i).data(500)
            if u == user:
                self.removeRow(i)
                return

    def _user_renamed(self, event: str, user: User, old_name: str, new_name: str) -> None:
        for i in range(self.rowCount()):
            u = self.item(i).data(500)
            if u == user:
                self.set_row(i, u)
                return

    def set_row(self, i: int, user: User) -> None:
        state, remaining = user.get_state()
        font = self._font_busy if state == 'Focus' else self._font_normal

        col1 = QtGui.QStandardItem()
        if state == 'Idle':
            txt = f'{user.get_name()}'
        else:
            txt = f'{user.get_name()}: {state}, {remaining} left'
        col1.setData(txt, Qt.DisplayRole)
        col1.setData(font, Qt.FontRole)
        col1.setData(user, 500)
        col1.setData('title', 501)
        col1.setData(txt, Qt.ItemDataRole.ToolTipRole)
        col1.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.setItem(i, 0, col1)

    def load(self, app: Tenant) -> None:
        self.clear()
        if app is not None:
            i = 0
            for user in app.values():
                if user.is_system_user():
                    continue
                item = QtGui.QStandardItem('')
                self.appendRow(item)
                self.set_row(i, user)
                i += 1
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))

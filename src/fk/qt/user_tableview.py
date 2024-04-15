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
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QHeaderView

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder
from fk.core.events import SourceMessagesProcessed
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.desktop.application import AfterSourceChanged, Application
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.actions import Actions
from fk.qt.user_model import UserModel


class UserTableView(AbstractTableView[Tenant, User]):
    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent,
                         source_holder,
                         UserModel(parent, source_holder),
                         'users_table',
                         actions,
                         'Loading, please wait...',
                         'Select a tenant.\nYou should never see this message. Please report a bug in GitHub.',
                         'There are no users.\nYou should never see this message. Please report a bug in GitHub.',
                         0)
        #application.on(AfterSourceChanged, self._on_source_changed)
        self._on_source_changed("", source_holder.get_source())

    def _on_source_changed(self, event, source):
        self.selectionModel().clear()
        self.upstream_selected(None)
        super()._on_source_changed(event, source)
        self._source_holder.on(SourceMessagesProcessed, self._on_messages)

    def update_actions(self, selected: User) -> None:
        pass

    @staticmethod
    def define_actions(actions: Actions):
        pass

    def upstream_selected(self, upstream: Tenant) -> None:
        super().upstream_selected(upstream)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _on_messages(self, event):
        self.upstream_selected(self._source_holder.get_data())

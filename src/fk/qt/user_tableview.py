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
from fk.core.app import App
from fk.core.user import User
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.user_model import UserModel


class UserTableView(AbstractTableView[App, User]):
    def __init__(self, parent: QWidget, source: AbstractEventSource, actions: dict[str, QAction]):
        super().__init__(parent,
                         source,
                         UserModel(parent, source),
                         'users_table',
                         actions,
                         'Loading, please wait...',
                         'Select a tenant.\nYou should never see this message. Please report a bug in GitHub.',
                         'There are no users.\nYou should never see this message. Please report a bug in GitHub.'
                         )

    def update_actions(self, selected: User) -> None:
        pass

    def create_actions(self) -> dict[str, QAction]:
        return dict()

    def upstream_selected(self, upstream: App) -> None:
        print(f'Loaded: {upstream}')
        super().upstream_selected(upstream)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

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

from PySide6.QtWidgets import QTableView, QWidget, QHeaderView

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import SourceMessagesProcessed
from fk.qt.user_model import UserModel


class UserTableView(QTableView, AbstractEventEmitter):
    _source: AbstractEventSource

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent,
                         allowed_events=[])
        self._source = source
        source.on(SourceMessagesProcessed, lambda event: self._on_data_loaded())

        self.setObjectName('users_table')
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QTableView.SelectionMode.NoSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(10)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)
        self.setVisible(False)

    def _on_data_loaded(self) -> None:
        user_model = UserModel(self, self._source)
        user_model.load()
        self.setModel(user_model)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.selectionModel().selectionChanged.connect(lambda s, d: self._on_selection_changed(s, d))

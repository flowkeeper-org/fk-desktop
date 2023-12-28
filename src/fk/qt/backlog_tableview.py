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

import datetime

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy
from fk.core.user import User
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.backlog_model import BacklogModel


class BacklogTableView(AbstractTableView[User, Backlog]):
    def __init__(self, parent: QWidget, source: AbstractEventSource, actions: dict[str, QAction]):
        super().__init__(parent,
                         source,
                         BacklogModel(parent, source),
                         'backlogs_table',
                         actions,
                         'Loading, please wait...',
                         'Select a user.\nYou should never see this message. Please report a bug in GitHub.',
                         "You haven't got any backlogs yet.\nCreate the first one by pressing Ctrl+N."
                         )
        self._init_menu(actions)

    def _init_menu(self, actions: dict[str, QAction]):
        menu: QMenu = QMenu()
        menu.addActions([
            actions['newBacklog'],
            actions['renameBacklog'],
            actions['deleteBacklog'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))

    def create_actions(self) -> dict[str, QAction]:
        return {
            'newBacklog': self._create_action("New Backlog", 'Ctrl+N', None, self.create_backlog),
            'renameBacklog': self._create_action("Rename Backlog", 'Ctrl+R', None, self.rename_selected_backlog),
            'deleteBacklog': self._create_action("Delete Backlog", 'F8', None, self.delete_selected_backlog),
        }

    def upstream_selected(self, user: User) -> None:
        super().upstream_selected(user)
        self._actions['newBacklog'].setEnabled(user is not None)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def update_actions(self, selected: Backlog) -> None:
        # It can be None for example if we don't have any backlogs left, or if
        # we haven't loaded any yet. BacklogModel supports None.
        is_backlog_selected = selected is not None
        self._actions['deleteBacklog'].setEnabled(is_backlog_selected)
        self._actions['renameBacklog'].setEnabled(is_backlog_selected)

    # Actions

    def create_backlog(self) -> None:
        prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
        new_name = generate_unique_name(prefix, self._source.backlogs())
        self._source.execute(CreateBacklogStrategy, [generate_uid(), new_name])

        # Start editing it. The new item will always be at the top of the list.
        index: QModelIndex = self.model().index(0, 0)
        self.setCurrentIndex(index)
        self.edit(index)

    def rename_selected_backlog(self) -> None:
        index: QModelIndex = self.currentIndex()
        if index is None:
            raise Exception("Trying to rename a backlog, while there's none selected")
        self.edit(index)

    def delete_selected_backlog(self) -> None:
        selected: Backlog = self.get_current()
        if selected is None:
            raise Exception("Trying to delete a backlog, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete backlog '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteBacklogStrategy, [selected.get_uid()])

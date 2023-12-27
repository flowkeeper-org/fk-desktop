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
from typing import Callable

from PySide6.QtCore import QItemSelection, Qt, QItemSelectionModel, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy
from fk.core.events import SourceMessagesProcessed
from fk.qt.backlog_model import BacklogModel

BeforeBacklogChanged = "BeforeBacklogChanged"
AfterBacklogChanged = "AfterBacklogChanged"


class BacklogTableView(QTableView, AbstractEventEmitter):
    _source: AbstractEventSource
    _action_new_backlog: QAction
    _action_rename_backlog: QAction
    _action_delete_backlog: QAction

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent,
                         allowed_events=[
                             BeforeBacklogChanged,
                             AfterBacklogChanged,
                         ])
        self._source = source
        source.on(SourceMessagesProcessed, lambda event: self._on_data_loaded())

        self.setObjectName('backlogs_table')
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(10)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._initialize_actions()
        self._on_selection_changed(None, None)

    def _create_action(self, text: str, shortcut: str, member: Callable) -> QAction:
        res: QAction = QAction(text, self)
        res.setShortcut(shortcut)
        res.triggered.connect(lambda: member())
        return res

    def _initialize_actions(self) -> None:
        menu: QMenu = QMenu()
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))

        self._action_new_backlog = self._create_action("New Backlog", 'Ctrl+N', self.create_backlog)
        menu.addAction(self._action_new_backlog)
        self._action_rename_backlog = self._create_action("Rename Backlog", 'Ctrl+R', self.rename_selected_backlog)
        menu.addAction(self._action_rename_backlog)
        self._action_delete_backlog = self._create_action("Delete Backlog", 'F8', self.delete_selected_backlog)
        menu.addAction(self._action_delete_backlog)

    def _on_data_loaded(self) -> None:
        backlog_model = BacklogModel(self, self._source)
        backlog_model.load()
        self.setModel(backlog_model)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.selectionModel().selectionChanged.connect(lambda s, d: self._on_selection_changed(s, d))

    def _get_selected_index(self) -> QModelIndex | None:
        model: QItemSelectionModel = self.selectionModel()
        if model is not None:
            indexes = model.selectedIndexes()
            if len(indexes) == 1:
                return indexes[0]

    def get_selected(self) -> Backlog | None:
        index = self._get_selected_index()
        if index is not None:
            return index.data(500)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        new_backlog: Backlog | None = None
        if selected is not None and selected.data():
            new_backlog = selected.data().topLeft().data(500)

        old_backlog: Backlog | None = None
        if deselected is not None and deselected.data():
            old_backlog = deselected.data().topLeft().data(500)

        params = {
            'before': old_backlog,
            'after': new_backlog,
        }
        self._emit(BeforeBacklogChanged, params)

        # It can be None for example if we don't have any backlogs left, or if
        # we haven't loaded any yet. BacklogModel supports None.
        is_backlog_selected = new_backlog is not None
        self._action_delete_backlog.setEnabled(is_backlog_selected)
        self._action_rename_backlog.setEnabled(is_backlog_selected)

        self._emit(AfterBacklogChanged, params)

    def create_backlog(self) -> None:
        prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
        new_name = generate_unique_name(prefix, self._source.backlogs())
        self._source.execute(CreateBacklogStrategy, [generate_uid(), new_name])

        # Start editing it. The new item will always be at the top of the list.
        index: QModelIndex = self.model().index(0, 0)
        self.setCurrentIndex(index)
        self.edit(index)

    def rename_selected_backlog(self) -> None:
        index: QModelIndex = self._get_selected_index()
        if index is None:
            raise Exception("Trying to rename a backlog, while there's none selected")
        self.edit(index)

    def delete_selected_backlog(self) -> None:
        selected: Backlog = self.get_selected()
        if selected is None:
            raise Exception("Trying to delete a backlog, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete backlog '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteBacklogStrategy, [selected.get_uid()])

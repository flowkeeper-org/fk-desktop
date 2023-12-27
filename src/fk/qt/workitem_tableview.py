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
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.qt.backlog_model import BacklogModel
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.workitem_model import WorkitemModel

BeforeWorkitemChanged = "BeforeWorkitemChanged"
AfterWorkitemChanged = "AfterWorkitemChanged"
BeforeWorkitemCompleted = "BeforeWorkitemCompleted"
AfterWorkitemCompleted = "AfterWorkitemCompleted"


class WorkitemTableView(QTableView, AbstractEventEmitter):
    _source: AbstractEventSource

    _action_new_workitem: QAction
    _action_rename_workitem: QAction
    _action_delete_workitem: QAction
    _action_complete_workitem: QAction

    # TODO: Are pomodoro actions part of the timer, or this table?
    # _action_: QAction
    # _action_: QAction
    # _action_: QAction
    # _action_: QAction
    # _action_: QAction

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent,
                         allowed_events=[
                             BeforeWorkitemChanged,
                             AfterWorkitemChanged,
                             BeforeWorkitemCompleted,
                             AfterWorkitemCompleted,
                         ])
        self._source = source
        source.on(SourceMessagesProcessed, lambda event: self._on_data_loaded())

        self.setObjectName('workitems_table')
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(10)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setItemDelegateForColumn(2, PomodoroDelegate())

        # Drag-and-drop doesn't work for some reason
        # workitems_table.setDragEnabled(True)
        # workitems_table.setAcceptDrops(True)
        # workitems_table.setDropIndicatorShown(True)
        # workitems_table.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
        # workitems_table.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        # workitems_table.setDragDropOverwriteMode(False)

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

        self._action_new_workitem = self._create_action("New Item", 'Ins', self.create_workitem)
        menu.addAction(self._action_new_workitem)
        self._action_rename_workitem = self._create_action("Rename Item", 'F2', self.rename_selected_workitem)
        menu.addAction(self._action_rename_workitem)
        self._action_complete_workitem = self._create_action("Complete Item", 'Ctrl+P', self.complete_selected_workitem)
        menu.addAction(self._action_complete_workitem)
        self._action_delete_workitem = self._create_action("Delete Item", 'Del', self.delete_selected_workitem)
        menu.addAction(self._action_delete_workitem)

    def _on_data_loaded(self) -> None:
        workitem_model = WorkitemModel(self, self._source)
        self.setModel(workitem_model)
        self.selectionModel().selectionChanged.connect(lambda s, d: self._on_selection_changed(s, d))

    def load_for_backlog(self, backlog: Backlog) -> None:
        if backlog is None:
            # TODO: Show "no data"
            pass
        else:
            self._action_new_workitem.setEnabled(True)
        self.model().load(backlog)  # Handles None alright
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def _get_selected_index(self) -> QModelIndex | None:
        model: QItemSelectionModel = self.selectionModel()
        if model is not None:
            indexes = model.selectedIndexes()
            if len(indexes) == 3:
                return indexes[1]

    def get_selected(self) -> Backlog | None:
        index = self._get_selected_index()
        if index is not None:
            return index.data(500)

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        # TODO: BUG: Create two WIs and delete the first. We receive TWO of those
        # events -- the first with correct WI, which is now selected, but the second
        # one is with None. We also receive a bunch of those events when we select
        # another backlog, which is weird. Should we filter those somehow?

        new_workitem: Workitem | None = None
        if selected is not None and selected.data():
            new_workitem = selected.data().topLeft().data(500)

        old_workitem: Workitem | None = None
        if deselected is not None and deselected.data():
            old_workitem = deselected.data().topLeft().data(500)

        print(f'New workitem is selected: {new_workitem}')

        params = {
            'before': old_workitem,
            'after': new_workitem,
        }
        self._emit(BeforeWorkitemChanged, params)

        # It can be None for example if we don't have any backlogs left, or if
        # we haven't loaded any yet. BacklogModel supports None.
        is_workitem_selected = new_workitem is not None
        self._action_delete_workitem.setEnabled(is_workitem_selected)
        self._action_rename_workitem.setEnabled(is_workitem_selected)
        # TODO + based on new_workitem.is_sealed()
        # complete
        # start
        # add_pomodoro
        # remove_pomodoro

        self._emit(AfterWorkitemChanged, params)

    def create_workitem(self) -> None:
        model = self.model()
        backlog: Backlog = model.get_backlog()
        if backlog is None:
            raise Exception("Trying to create a workitem while there's no backlog selected")

        new_name = generate_unique_name("Do something", backlog)
        self._source.execute(CreateWorkitemStrategy, [generate_uid(), backlog.get_uid(), new_name])

        # Start editing it. The new item will always be at the end of the list.
        index: QModelIndex = model.index(model.rowCount() - 1, 1)
        self.setCurrentIndex(index)
        self.edit(index)

    def rename_selected_workitem(self) -> None:
        index: QModelIndex = self._get_selected_index()
        if index is None:
            raise Exception("Trying to rename a workitem, while there's none selected")
        self.edit(index)

    def delete_selected_workitem(self) -> None:
        selected: Workitem = self.get_selected()
        if selected is None:
            raise Exception("Trying to delete a workitem, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete workitem '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteWorkitemStrategy, [selected.get_uid()])

    def complete_selected_workitem(self) -> None:
        selected: Workitem = self.get_selected()
        if selected is None:
            raise Exception("Trying to complete a workitem, while there's none selected")
        params = {
            'workitem': selected
        }
        self._emit(BeforeWorkitemCompleted, params)
        if not selected.has_running_pomodoro() or QMessageBox().warning(
                self,
                "Confirmation",
                f"Are you sure you want to complete current workitem? This will void current pomodoro.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Cancel
                ) == QMessageBox.StandardButton.Ok:
            self._source.execute(CompleteWorkitemStrategy, [selected.get_uid(), "finished"])
        self._emit(AfterWorkitemCompleted, params)

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

from typing import Callable

from PySide6.QtCore import QItemSelection, Qt, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QTableView, QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.pomodoro_strategies import StartWorkStrategy, AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.workitem_model import WorkitemModel

BeforeWorkitemChanged = "BeforeWorkitemChanged"
AfterWorkitemChanged = "AfterWorkitemChanged"


class WorkitemTableView(QTableView, AbstractEventEmitter):
    _source: AbstractEventSource
    _is_loaded: bool

    _action_new_workitem: QAction
    _action_rename_workitem: QAction
    _action_delete_workitem: QAction

    _action_start_workitem: QAction
    _action_complete_workitem: QAction

    _action_add_pomodoro: QAction
    _action_remove_pomodoro: QAction

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent,
                         allowed_events=[
                             BeforeWorkitemChanged,
                             AfterWorkitemChanged,
                         ])
        self._source = source
        self._is_loaded = False
        self.setModel(WorkitemModel(self, self._source))
        self.selectionModel().currentRowChanged.connect(lambda s, d: self._on_current_changed(s, d))

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
        self._on_current_changed(None, None)

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
        self._action_delete_workitem = self._create_action("Delete Item", 'Del', self.delete_selected_workitem)
        menu.addAction(self._action_delete_workitem)

        self._action_start_workitem = self._create_action("Start Item", 'Ctrl+S', self.start_selected_workitem)
        menu.addAction(self._action_start_workitem)
        self._action_complete_workitem = self._create_action("Complete Item", 'Ctrl+P', self.complete_selected_workitem)
        menu.addAction(self._action_complete_workitem)

        self._action_add_pomodoro = self._create_action("Add Pomodoro", 'Ctrl++', self.add_to_selected_workitem)
        menu.addAction(self._action_add_pomodoro)
        self._action_remove_pomodoro = self._create_action("Remove Pomodoro", 'Ctrl+-', self.remove_from_selected_workitem)
        menu.addAction(self._action_remove_pomodoro)

    def load_for_backlog(self, backlog: Backlog) -> None:
        if backlog is None:
            # TODO: Show "no data"
            self._action_new_workitem.setEnabled(False)
            self._is_loaded = False
        else:
            self._action_new_workitem.setEnabled(True)
            self._is_loaded = True
        self.model().load(backlog)  # Handles None alright
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def get_current(self) -> Backlog | None:
        index = self.currentIndex()
        if index is not None:
            return index.data(500)

    def _on_current_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        new_workitem: Workitem | None = None
        if selected is not None:
            new_workitem = selected.data(500)

        old_workitem: Workitem | None = None
        if deselected is not None:
            old_workitem = deselected.data(500)

        print(f'Trace - Workitems::Current changed to {new_workitem}')

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
        self._action_start_workitem.setEnabled(is_workitem_selected)
        self._action_complete_workitem.setEnabled(is_workitem_selected)
        self._action_add_pomodoro.setEnabled(is_workitem_selected)
        self._action_remove_pomodoro.setEnabled(is_workitem_selected)
        # TODO + based on new_workitem.is_sealed() and if there are pomos available

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
        index: QModelIndex = self.currentIndex()
        if index is None:
            raise Exception("Trying to rename a workitem, while there's none selected")
        self.edit(index)

    def delete_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to delete a workitem, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete workitem '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteWorkitemStrategy, [selected.get_uid()])

    def start_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to start a workitem, while there's none selected")
        self._source.execute(StartWorkStrategy, [
            selected.get_uid(),
            self._source.get_config_parameter('Pomodoro.default_work_duration')
        ])

    def complete_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to complete a workitem, while there's none selected")
        if not selected.has_running_pomodoro() or QMessageBox().warning(
                self,
                "Confirmation",
                f"Are you sure you want to complete current workitem? This will void current pomodoro.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Cancel
                ) == QMessageBox.StandardButton.Ok:
            self._source.execute(CompleteWorkitemStrategy, [selected.get_uid(), "finished"])

    def add_to_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to add pomodoro to a workitem, while there's none selected")
        self._source.execute(AddPomodoroStrategy, [
            selected.get_uid(),
            "1"
        ])

    def remove_from_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to remove pomodoro from a workitem, while there's none selected")
        self._source.execute(RemovePomodoroStrategy, [
            selected.get_uid(),
            "1"
        ])

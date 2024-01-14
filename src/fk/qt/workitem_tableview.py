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

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.events import AfterWorkitemCreate, SourceMessagesProcessed
from fk.core.pomodoro_strategies import StartWorkStrategy, AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.desktop.application import AfterSourceChanged, Application
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.workitem_model import WorkitemModel


class WorkitemTableView(AbstractTableView[Backlog, Workitem]):
    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source: AbstractEventSource,
                 actions: dict[str, QAction]):
        super().__init__(parent,
                         source,
                         WorkitemModel(parent, source),
                         'workitems_table',
                         actions,
                         'Loading, please wait...',
                         '← Select a backlog.',
                         'The selected backlog is empty.\nCreate the first workitem by pressing Ins key.',
                         1)
        self.setItemDelegateForColumn(2, PomodoroDelegate())
        self._init_menu(actions)
        actions['showCompleted'].toggled.connect(self._toggle_show_completed_workitems)
        #application.on(AfterSourceChanged, self._on_source_changed)
        self._on_source_changed("", source)

    def _on_source_changed(self, event, source):
        self.selectionModel().clear()
        self.upstream_selected(None)
        super()._on_source_changed(event, source)
        source.on(AfterWorkitemCreate, self._on_new_workitem)
        source.on(SourceMessagesProcessed, self._on_messages)

    def _init_menu(self, actions: dict[str, QAction]):
        menu: QMenu = QMenu()
        menu.addActions([
            actions['newItem'],
            actions['renameItem'],
            actions['deleteItem'],
            actions['startItem'],
            actions['completeItem'],
            actions['addPomodoro'],
            actions['removePomodoro'],
            actions['showCompleted'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))

    def create_actions(self) -> dict[str, QAction]:
        return {
            'newItem': self._create_action("New Item", 'Ins', None, self.create_workitem),
            'renameItem': self._create_action("Rename Item", 'F2', None, self.rename_selected_workitem),
            'deleteItem': self._create_action("Delete Item", 'Del', None, self.delete_selected_workitem),
            'startItem': self._create_action("Start Item", 'Ctrl+S', ":/icons/tool-next.svg", self.start_selected_workitem),
            'completeItem': self._create_action("Complete Item", 'Ctrl+P', ":/icons/tool-complete.svg", self.complete_selected_workitem),
            'addPomodoro': self._create_action("Add Pomodoro", 'Ctrl++', None, self.add_pomodoro),
            'removePomodoro': self._create_action("Remove Pomodoro", 'Ctrl+-', None, self.remove_pomodoro),
            'showCompleted': self._create_action("Show completed workitems", '', None, self._toggle_show_completed_workitems, True, True),
        }

    def upstream_selected(self, backlog: Backlog) -> None:
        super().upstream_selected(backlog)
        self._actions['newItem'].setEnabled(backlog is not None)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def update_actions(self, selected: Workitem) -> None:
        # It can be None for example if we don't have any backlogs left, or if we haven't loaded any yet.
        is_workitem_selected = selected is not None
        self._actions['deleteItem'].setEnabled(is_workitem_selected)
        self._actions['renameItem'].setEnabled(is_workitem_selected)
        self._actions['startItem'].setEnabled(is_workitem_selected)
        self._actions['completeItem'].setEnabled(is_workitem_selected)
        self._actions['addPomodoro'].setEnabled(is_workitem_selected)
        self._actions['removePomodoro'].setEnabled(is_workitem_selected)
        # TODO + based on new_workitem.is_sealed() and if there are pomodoros available

    # Actions

    def create_workitem(self) -> None:
        model = self.model()
        backlog: Backlog = model.get_backlog()
        if backlog is None:
            raise Exception("Trying to create a workitem while there's no backlog selected")
        new_name = generate_unique_name("Do something", backlog.names())
        self._source.execute(CreateWorkitemStrategy,
                             [generate_uid(), backlog.get_uid(), new_name],
                             carry="edit")

        # A simpler, more efficient, but a bit uglier single-step alternative
        # (new_name, ok) = QInputDialog.getText(self,
        #                                       "New item",
        #                                       "Provide a name for the new item",
        #                                       text="Do something")
        # if ok:
        #     self._source.execute(CreateWorkitemStrategy, [generate_uid(), backlog.get_uid(), new_name])

    def _on_new_workitem(self, workitem: Workitem, carry: any, **kwargs):
        if carry == 'edit':
            index: QModelIndex = self.select(workitem)
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

    def add_pomodoro(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to add pomodoro to a workitem, while there's none selected")
        self._source.execute(AddPomodoroStrategy, [
            selected.get_uid(),
            "1"
        ])

    def remove_pomodoro(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to remove pomodoro from a workitem, while there's none selected")
        self._source.execute(RemovePomodoroStrategy, [
            selected.get_uid(),
            "1"
        ])

    def _toggle_show_completed_workitems(self, checked: bool) -> None:
        self.model().show_completed(checked)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

    def _on_messages(self, event):
        self.upstream_selected(None)

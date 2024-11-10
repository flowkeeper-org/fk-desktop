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
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemCreate, AfterSettingsChanged
from fk.core.pomodoro_strategies import StartWorkStrategy, AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.tag import Tag
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.desktop.application import Application
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.actions import Actions
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.workitem_model import WorkitemModel
from fk.qt.workitem_text_delegate import WorkitemTextDelegate


class WorkitemTableView(AbstractTableView[Backlog | Tag, Workitem]):
    _application: Application
    _menu: QMenu

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent,
                         source_holder,
                         WorkitemModel(parent, source_holder),
                         'workitems_table',
                         actions,
                         'Loading, please wait...',
                         '← Select a backlog or tag.',
                         'The selected backlog is empty.\nCreate the first workitem by pressing Ins key.',
                         1)
        self._application = application
        self._configure_delegate()
        self._menu = self._init_menu(actions)
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.update_actions(None)
        application.get_settings().on(AfterSettingsChanged, self._on_setting_changed)

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.theme' in new_values or 'Application.feature_tags' in new_values:
            self._configure_delegate()
            self._resize()

    def _is_tags_enabled(self) -> bool:
        return self._application.get_settings().get('Application.feature_tags') == 'True'

    def _configure_delegate(self):
        # Workitem text -- HTML or no delegate
        if self._is_tags_enabled():
            self.setItemDelegateForColumn(1,
                                          WorkitemTextDelegate(self,
                                                               self._application.get_icon_theme(),
                                                               self._application.get_theme_variables()['TABLE_TEXT_COLOR']))
        else:
            self.setItemDelegateForColumn(1, None)

        # Pomodoros display
        self.setItemDelegateForColumn(2,
                                      PomodoroDelegate(self,
                                                       self._application.get_icon_theme()))

    def _update_actions_if_needed(self, workitem: Workitem):
        current = self.get_current()
        if workitem == current:
            self.update_actions(current)

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        super()._on_source_changed(event, source)
        source.on(AfterWorkitemCreate, self._on_new_workitem)
        source.on("AfterWorkitem*",
                  lambda workitem, **kwargs: self._update_actions_if_needed(workitem))
        source.on("AfterPomodoro*",
                  lambda workitem, **kwargs: self._update_actions_if_needed(workitem))
        self.selectionModel().clear()
        self.upstream_selected(None)

    def _init_menu(self, actions: Actions) -> QMenu:
        menu: QMenu = QMenu()
        menu.addActions([
            actions['workitems_table.newItem'],
            actions['workitems_table.renameItem'],
            actions['workitems_table.deleteItem'],
            actions['workitems_table.startItem'],
            actions['workitems_table.completeItem'],
            actions['workitems_table.addPomodoro'],
            actions['workitems_table.removePomodoro'],
            actions['workitems_table.showCompleted'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))
        return menu

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('workitems_table.newItem', "New Item", 'Ins', "tool-add", WorkitemTableView.create_workitem)
        actions.add('workitems_table.renameItem', "Rename Item", 'F6', "tool-rename", WorkitemTableView.rename_selected_workitem)
        actions.add('workitems_table.deleteItem', "Delete Item", 'Del', "tool-delete", WorkitemTableView.delete_selected_workitem)
        actions.add('workitems_table.startItem', "Start Item", 'Ctrl+S', "tool-start-item", WorkitemTableView.start_selected_workitem)
        actions.add('workitems_table.completeItem', "Complete Item", 'Ctrl+P', "tool-complete-item", WorkitemTableView.complete_selected_workitem)
        actions.add('workitems_table.addPomodoro', "Add Pomodoro", 'Ctrl++', "tool-add-pomodoro", WorkitemTableView.add_pomodoro)
        actions.add('workitems_table.removePomodoro', "Remove Pomodoro", 'Ctrl+-', "tool-remove-pomodoro", WorkitemTableView.remove_pomodoro)
        actions.add('workitems_table.showCompleted',
                    "Show Completed Items",
                    '',
                    "tool-show-completed",
                    WorkitemTableView._toggle_show_completed_workitems,
                    True,
                    actions.get_settings().get('Application.show_completed') == 'True')

    def upstream_selected(self, backlog_or_tag: Backlog | Tag) -> None:
        super().upstream_selected(backlog_or_tag)
        self._actions['workitems_table.newItem'].setEnabled(type(backlog_or_tag) is Backlog)
        self._resize()

    def update_actions(self, selected: Workitem) -> None:
        # It can be None for example if we don't have any backlogs left, or if we haven't loaded any yet.
        # TODO: Call this on any workitem and timer event
        is_workitem_selected = selected is not None
        is_workitem_editable = is_workitem_selected and not selected.is_sealed()
        self._actions['workitems_table.deleteItem'].setEnabled(is_workitem_selected)
        self._actions['workitems_table.renameItem'].setEnabled(is_workitem_editable)
        self._actions['workitems_table.startItem'].setEnabled(is_workitem_editable and selected.is_startable())
        self._actions['workitems_table.completeItem'].setEnabled(is_workitem_editable)
        self._actions['workitems_table.addPomodoro'].setEnabled(is_workitem_editable)
        self._actions['workitems_table.removePomodoro'].setEnabled(is_workitem_editable and selected.is_startable())

    # Actions

    def create_workitem(self) -> None:
        model = self.model()
        backlog_or_tag: Backlog | Tag = model.get_backlog_or_tag()
        if backlog_or_tag is None:
            raise Exception("Trying to create a workitem while there's no backlog nor tag selected")
        if type(backlog_or_tag) is Tag:
            raise Exception("Trying to create a workitem directly in a tag -- shouldn't be possible")
        backlog: Backlog = backlog_or_tag
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
        settings = self._source.get_settings()
        self._source.execute(StartWorkStrategy, [
            selected.get_uid(),
            settings.get('Pomodoro.default_work_duration'),
            settings.get('Pomodoro.default_rest_duration'),
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
        self._resize()
        self._source.set_config_parameters({'Application.show_completed': str(checked)})

    def _resize(self) -> None:
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        # Resizing to contents results in visible blinking on Kubuntu 20.04, so cannot be enabled by default.
        self.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents if self._is_tags_enabled() else QHeaderView.ResizeMode.Fixed)

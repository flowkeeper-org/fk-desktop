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
import logging

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox, QInputDialog

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterBacklogCreate, SourceMessagesProcessed
from fk.core.pomodoro import POMODORO_TYPE_NORMAL
from fk.core.pomodoro_strategies import AddPomodoroStrategy
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy
from fk.desktop.application import Application
from fk.qt.abstract_tableview import AbstractTableView, AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.backlog_model import BacklogModel
from fk.qt.cached_websocket_event_source import CachedWebsocketEventSource

logger = logging.getLogger(__name__)


class BacklogTableView(AbstractTableView[User, Backlog]):
    _application: Application
    _menu: QMenu

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent,
                         source_holder,
                         BacklogModel(parent, source_holder),
                         'backlogs_table',
                         actions,
                         'Loading, please wait...',
                         'No data or connection error.',
                         "You haven't got any backlogs yet. Create the first one by pressing Ctrl+N.",
                         0)
        self._menu = self._init_menu(actions)
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.on(AfterSelectionChanged, lambda event, before, after: self._application.get_settings().set({
            'Application.last_selected_backlog': after.get_uid() if after is not None else ''
        }))
        self._application = application
        self.update_actions(None)

    def _lock_ui(self, event, after: int, last_received: datetime.datetime) -> None:
        self.update_actions(self.get_current())

    def _unlock_ui(self, event, ping: int) -> None:
        self.update_actions(self.get_current())

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        super()._on_source_changed(event, source)
        self.selectionModel().clear()
        self.upstream_selected(None)

        source.on(AfterBacklogCreate, self._on_new_backlog)
        source.on(SourceMessagesProcessed, self._on_messages)

        # This is done to update the "New backlog from incomplete" action, which depends on the child workitems
        source.on("AfterWorkitem*",
                  lambda workitem, **kwargs: self._update_actions_if_needed(workitem))
        source.on('AfterPomodoro*',
                  lambda **kwargs: self._update_actions_if_needed(
                      kwargs['workitem'] if 'workitem' in kwargs else kwargs['pomodoro'].get_parent()
                  ))

        # TODO: Check if it's a caching source. There's no need to lock UI for caching sources.
        # source.on(events.WentOffline, self._lock_ui)
        # source.on(events.WentOnline, self._unlock_ui)

    def _init_menu(self, actions: Actions) -> QMenu:
        menu: QMenu = QMenu()
        menu.addActions([
            actions['backlogs_table.newBacklog'],
            actions['backlogs_table.newBacklogFromIncomplete'],
            actions['backlogs_table.renameBacklog'],
            actions['backlogs_table.deleteBacklog'],
            # Uncomment to troubleshoot
            # actions['backlogs_table.dumpBacklog'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))
        return menu

    def upstream_selected(self, user: User) -> None:
        super().upstream_selected(user)
        self._actions['backlogs_table.newBacklog'].setEnabled(user is not None)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _update_actions_if_needed(self, workitem: Workitem):
        if workitem is not None:
            updated: Backlog = workitem.get_parent()
            current = self.get_current()
            if updated == current:
                self.update_actions(current)

    def update_actions(self, selected: Backlog) -> None:
        logger.debug(f'Backlog table - update_actions({selected})')
        # It can be None for example if we don't have any backlogs left, or if
        # we haven't loaded any yet. BacklogModel supports None.
        is_backlog_selected = selected is not None

        is_incomplete = is_backlog_selected and next(selected.get_incomplete_workitems(), None) is not None

        source = self._application.get_source_holder().get_source()
        is_online = (source is None
                     or not source.can_connect()
                     or source.is_online()
                     or type(source) is CachedWebsocketEventSource)
        logger.debug(f' - Online: {is_online}')
        logger.debug(f' - Backlog selected: {is_backlog_selected}')
        logger.debug(f' - Has incomplete workitems: {is_incomplete}')

        self._actions['backlogs_table.newBacklog'].setEnabled(is_online)
        self._actions['backlogs_table.newBacklogFromIncomplete'].setEnabled(is_backlog_selected and
                                                                            is_online and
                                                                            is_incomplete)
        self._actions['backlogs_table.renameBacklog'].setEnabled(is_backlog_selected and is_online)
        self._actions['backlogs_table.deleteBacklog'].setEnabled(is_backlog_selected and is_online)
        self._actions['backlogs_table.dumpBacklog'].setEnabled(is_backlog_selected)
        # TODO: Double-clicking the backlog name doesn't use those

    def _on_new_backlog(self, backlog: Backlog, carry: any = None, **kwargs):
        if carry == 'edit':
            index: QModelIndex = self.select(backlog)
            self.edit(index)
        elif carry == 'select':
            self.select(backlog)

    def _on_messages(self, event: str, source: AbstractEventSource, carry: any = None) -> None:
        user = source.get_data().get_current_user()
        self.upstream_selected(user)
        last_selected_oid = self._application.get_settings().get('Application.last_selected_backlog')
        if user is not None and last_selected_oid != '' and last_selected_oid in user:
            self.select(user[last_selected_oid])

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('backlogs_table.newBacklog',
                    "New Backlog",
                    'Ctrl+N',
                    "tool-add",
                    BacklogTableView.create_backlog)
        actions.add('backlogs_table.newBacklogFromIncomplete',
                    "New Backlog From Incomplete",
                    'Ctrl+M',
                    "tool-add-prefilled",
                    BacklogTableView.create_backlog_from_incomplete)
        actions.add('backlogs_table.renameBacklog',
                    "Rename Backlog",
                    'Ctrl+R',
                    "tool-rename",
                    BacklogTableView.rename_selected_backlog)
        actions.add('backlogs_table.deleteBacklog',
                    "Delete Backlog",
                    'F8',
                    "tool-delete",
                    BacklogTableView.delete_selected_backlog)
        actions.add('backlogs_table.dumpBacklog',
                    "Dump (DEBUG)",
                    'Ctrl+D',
                    None,
                    BacklogTableView.dump_selected_backlog)

    # Actions

    def create_backlog(self) -> str:
        prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
        new_name = generate_unique_name(prefix, self._source.get_data().get_current_user().names())
        new_uid = generate_uid()
        self._source.execute(CreateBacklogStrategy, [new_uid, new_name], carry='edit')
        return new_uid

    def create_backlog_from_incomplete(self) -> str:
        selected = self.get_current()
        # A sanity check, just in case
        if selected is None:
            logger.error(f'Trying to create a backlog from incomplete, while there is none selected. Actions '
                         f'visibility should prevent this from happening.')
            return

        added_workitems = 0
        new_backlog_uid = self.create_backlog()
        for workitem in selected.get_incomplete_workitems():
            new_workitem_uid = generate_uid()
            self._source.execute(CreateWorkitemStrategy,
                                 [new_workitem_uid, new_backlog_uid, workitem.get_name()],
                                 carry="")  # Note that we don't carry "edit" in this case
            added_workitems += 1
            incomplete_pomodoros = list(workitem.get_incomplete_pomodoros())
            pomodoros_to_add = len(incomplete_pomodoros)
            if pomodoros_to_add > 0 and incomplete_pomodoros[0].get_type() == POMODORO_TYPE_NORMAL:
                self._source.execute(AddPomodoroStrategy,
                                     [new_workitem_uid, str(pomodoros_to_add)])

        if added_workitems == 0:
            logger.warning(f'Created a backlog from incomplete, but without any workitems. Actions '
                           f'visibility should prevent this from happening.')

        return new_backlog_uid

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

    def dump_selected_backlog(self) -> None:
        selected: Backlog = self.get_current()
        if selected is None:
            raise Exception("Trying to dump a backlog, while there's none selected")
        QInputDialog.getMultiLineText(None,
                                      "Backlog dump",
                                      "Technical information for debug / development purposes",
                                      selected.dump())

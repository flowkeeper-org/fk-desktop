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

from PySide6.QtCore import QModelIndex
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QMessageBox, QInputDialog, QVBoxLayout, QToolButton, QPushButton, QHBoxLayout, \
    QTextEdit, QLineEdit

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.backlog_tableview import BacklogTableView


class BacklogWidget(QWidget):
    _backlogs_table: BacklogTableView
    _source_holder: EventSourceHolder

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent)
        self._source_holder = source_holder
        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)
        self.setLayout(vlayout)

        hlayout = QHBoxLayout(self)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(0)
        vlayout.addLayout(hlayout)

        button = QPushButton(self)
        button.setIcon(QIcon(":/icons/tool-add.svg"))
        button.clicked.connect(actions['backlogs_table.newBacklog'].trigger)
        button.setText('Add')
        #button.setFixedHeight(30)
        hlayout.addWidget(button)

        button = QPushButton(self)
        button.setIcon(QIcon(":/icons/tool-delete.svg"))
        button.clicked.connect(actions['backlogs_table.deleteBacklog'].trigger)
        button.setText('Delete')
        #button.setFixedHeight(30)
        hlayout.addWidget(button)

        button = QPushButton(self)
        button.setIcon(QIcon(":/icons/tool-rename.svg"))
        button.clicked.connect(actions['backlogs_table.renameBacklog'].trigger)
        button.setText('Rename')
        #button.setFixedHeight(30)
        hlayout.addWidget(button)

        self._backlogs_table = BacklogTableView(self, application, source_holder, actions)
        vlayout.addWidget(self._backlogs_table)

    def on(self, event_pattern: str, callback: Callable, last: bool = False) -> None:
        self._backlogs_table.on(event_pattern, callback, last)

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('backlogs_table.newBacklog', "New Backlog", 'Ctrl+N', None, BacklogWidget.create_backlog)
        actions.add('backlogs_table.renameBacklog', "Rename Backlog", 'Ctrl+R', None, BacklogWidget.rename_selected_backlog)
        actions.add('backlogs_table.deleteBacklog', "Delete Backlog", 'F8', None, BacklogWidget.delete_selected_backlog)
        actions.add('backlogs_table.dumpBacklog', "Dump (DEBUG)", 'Ctrl+D', None, BacklogWidget.dump_selected_backlog)

    # Actions

    def create_backlog(self) -> None:
        prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
        new_name = generate_unique_name(prefix, self._source_holder.get_source().get_data().get_current_user().names())
        self._source_holder.get_source().execute(CreateBacklogStrategy, [generate_uid(), new_name], carry='edit')

    def rename_selected_backlog(self) -> None:
        index: QModelIndex = self._backlogs_table.currentIndex()
        if index is None:
            raise Exception("Trying to rename a backlog, while there's none selected")
        self._backlogs_table.edit(index)

    def delete_selected_backlog(self) -> None:
        selected: Backlog = self._backlogs_table.get_current()
        if selected is None:
            raise Exception("Trying to delete a backlog, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete backlog '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source_holder.get_source().execute(DeleteBacklogStrategy, [selected.get_uid()])

    def dump_selected_backlog(self) -> None:
        selected: Backlog = self._backlogs_table.get_current()
        if selected is None:
            raise Exception("Trying to dump a backlog, while there's none selected")
        QInputDialog.getMultiLineText(None,
                                      "Backlog dump",
                                      "Technical information for debug / development purposes",
                                      selected.dump())

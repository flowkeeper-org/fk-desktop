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
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout

from fk.core.event_source_holder import EventSourceHolder
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.configurable_toolbar import ConfigurableToolBar


class BacklogWidget(QWidget):
    _backlogs_table: BacklogTableView
    _source_holder: EventSourceHolder

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent)
        self.setObjectName('backlogs_widget')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self._source_holder = source_holder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        tb = ConfigurableToolBar(self, actions, "backlogs_toolbar")
        tb.addAction(actions['backlogs_table.newBacklog'])
        tb.addAction(actions['backlogs_table.newBacklogFromIncomplete'])
        tb.addAction(actions['backlogs_table.deleteBacklog'])
        tb.addAction(actions['backlogs_table.renameBacklog'])
        layout.addWidget(tb)

        self._backlogs_table = BacklogTableView(self, application, source_holder, actions)
        layout.addWidget(self._backlogs_table)

    def get_table(self):
        return self._backlogs_table

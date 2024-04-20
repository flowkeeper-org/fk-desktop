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
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton, QHBoxLayout

from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.workitem_tableview import WorkitemTableView


class WorkitemWidget(QWidget):
    _workitems_table: WorkitemTableView
    _source_holder: EventSourceHolder

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent)
        self.setObjectName('workitems_widget')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self._source_holder = source_holder
        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setSpacing(0)
        self.setLayout(vlayout)

        hlayout = QHBoxLayout(self)
        hlayout.setContentsMargins(5, 5, 5, 0)
        hlayout.setSpacing(5)
        vlayout.addLayout(hlayout)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.newItem'])
        button.setObjectName('top.newItem')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.deleteItem'])
        button.setObjectName('top.deleteItem')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.renameItem'])
        button.setObjectName('top.renameItem')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.startItem'])
        button.setObjectName('top.startItem')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.completeItem'])
        button.setObjectName('top.completeItem')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.addPomodoro'])
        button.setObjectName('top.addPomodoro')
        hlayout.addWidget(button)

        button = QToolButton(self)
        button.setDefaultAction(actions['workitems_table.removePomodoro'])
        button.setObjectName('top.removePomodoro')
        hlayout.addWidget(button)

        hlayout.addStretch()

        self._workitems_table = WorkitemTableView(self, application, source_holder, actions)
        vlayout.addWidget(self._workitems_table)

    def get_table(self) -> WorkitemTableView:
        return self._workitems_table

    def upstream_selected(self, backlog: Backlog | None) -> None:
        self._workitems_table.upstream_selected(backlog)

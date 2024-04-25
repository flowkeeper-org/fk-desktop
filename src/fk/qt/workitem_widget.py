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

from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder
from fk.core.events import AfterSettingsChanged
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.configurable_toolbar import ConfigurableToolBar
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        tb = ConfigurableToolBar(self, actions)
        tb.addAction(actions['workitems_table.newItem'])
        tb.addAction(actions['workitems_table.deleteItem'])
        tb.addAction(actions['workitems_table.renameItem'])
        tb.addAction(actions['workitems_table.startItem'])
        tb.addAction(actions['workitems_table.completeItem'])
        tb.addAction(actions['workitems_table.addPomodoro'])
        tb.addAction(actions['workitems_table.removePomodoro'])
        layout.addWidget(tb)

        self._workitems_table = WorkitemTableView(self, application, source_holder, actions)
        layout.addWidget(self._workitems_table)

        application.get_settings().on(AfterSettingsChanged, self.on_setting_changed)

    def get_table(self) -> WorkitemTableView:
        return self._workitems_table

    def upstream_selected(self, backlog: Backlog | None) -> None:
        self._workitems_table.upstream_selected(backlog)

    def on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.show_toolbar' in new_values:
            show = new_values['Application.show_toolbar'] == 'True'
            print(f'Show workitem toolbar: {show}')

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

from PySide6.QtWidgets import QMenuBar

from fk.desktop.application import Application
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.focus_widget import FocusWidget
from fk.qt.minimal_common import window, main_loop, actions, app
from fk.qt.user_tableview import UserTableView
from fk.qt.workitem_tableview import WorkitemTableView

Application.define_actions(actions)
BacklogTableView.define_actions(actions)
UserTableView.define_actions(actions)
WorkitemTableView.define_actions(actions)
FocusWidget.define_actions(actions)

actions.bind('application', app)

menu = QMenuBar(window)
menu.addActions(actions.all())
window.setCentralWidget(menu)

print('All actions:')
print('\n'.join([action.objectName() for action in actions.all()]))

main_loop()

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
from fk.core.tenant import Tenant
from fk.qt.user_tableview import UserTableView
from fk.tools.minimal_common import MinimalCommon


def on_data(root: Tenant):
    print('on_data', root)
    users_table.upstream_selected(root)


mc = MinimalCommon(on_data)

app = mc.get_app()
window = mc.get_window()
actions = mc.get_actions()

UserTableView.define_actions(actions)
users_table: UserTableView = UserTableView(window, app, app.get_source_holder(), actions)
actions.bind('users_table', users_table)
window.setCentralWidget(users_table)

mc.main_loop()

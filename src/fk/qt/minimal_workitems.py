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

from fk.qt.minimal_common import source, window, app, root, main_loop, actions
from fk.qt.workitem_tableview import WorkitemTableView

window.resize(600, 400)
WorkitemTableView.define_actions(actions)
workitems_table: WorkitemTableView = WorkitemTableView(window, app, source, actions)
actions.bind('workitems_table', workitems_table)
window.setCentralWidget(workitems_table)

main_loop(lambda: workitems_table.upstream_selected(
    list(root.get_current_user().values())[0]
))

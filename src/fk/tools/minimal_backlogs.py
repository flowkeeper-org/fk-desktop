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

from fk.qt.backlog_tableview import BacklogTableView
from fk.tools.minimal_common import window, app, main_loop, actions

BacklogTableView.define_actions(actions)
backlogs_table: BacklogTableView = BacklogTableView(window, app, app.get_source_holder(), actions)
actions.bind('backlogs_table', backlogs_table)
window.setCentralWidget(backlogs_table)

main_loop(lambda root: backlogs_table.upstream_selected(root.get_current_user()))

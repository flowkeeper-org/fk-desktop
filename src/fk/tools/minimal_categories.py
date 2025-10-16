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
from fk.qt.category_tableview import CategoryTableView
from fk.tools.minimal_common import MinimalCommon

mc = MinimalCommon(lambda root: categories_table.upstream_selected(root.get_current_user().get_root_category()))

CategoryTableView.define_actions(mc.get_actions())
categories_table: CategoryTableView = CategoryTableView(
    mc.get_window(),
    mc.get_app(),
    mc.get_app().get_source_holder(),
    mc.get_actions(),
    '#root')
mc.get_actions().bind('categories_table', categories_table)

mc.get_window().setCentralWidget(categories_table)

mc.main_loop()

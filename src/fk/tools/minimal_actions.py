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

import logging

from PySide6.QtWidgets import QMenuBar

from fk.desktop.application import Application
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.focus_widget import FocusWidget
from fk.qt.user_tableview import UserTableView
from fk.qt.workitem_tableview import WorkitemTableView
from fk.tools.minimal_common import MinimalCommon

logger = logging.getLogger(__name__)

mc = MinimalCommon()

Application.define_actions(mc.get_actions())
BacklogTableView.define_actions(mc.get_actions())
UserTableView.define_actions(mc.get_actions())
WorkitemTableView.define_actions(mc.get_actions())
FocusWidget.define_actions(mc.get_actions())

mc.get_actions().bind('application', mc.get_app())

menu = QMenuBar(mc.get_window())
menu.addActions(mc.get_actions().all())
mc.get_window().setCentralWidget(menu)

logger.debug('All actions:')
for action in mc.get_actions().all():
    logger.debug(action.objectName())

mc.main_loop()

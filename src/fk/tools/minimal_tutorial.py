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
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPushButton, QWidget

from fk.qt.info_overlay import show_tutorial
from fk.tools.minimal_common import MinimalCommon


def get_tutorial_step(step: int, widget: QWidget) -> (str, QPoint, str):
    if step == 1:
        return 'Welcome to Flowkeeper!', widget.mapToGlobal(widget.rect().topLeft()), 'info'
    elif step == 2:
        return 'Tutorial step 2 with a somewhat longer description', widget.mapToGlobal(widget.rect().bottomRight()), 'arrow'
    elif step == 3:
        return 'Thank you!', widget.mapToGlobal(widget.rect().center()), 'info'


mc = MinimalCommon(initialize_source=False)
button = QPushButton(mc.get_window())
button.setFixedWidth(300)
button.setText('Tutorial')
button.clicked.connect(lambda: show_tutorial(lambda step: get_tutorial_step(step, button), 250))
mc.get_window().setCentralWidget(button)

mc.main_loop()

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

from PySide6.QtWidgets import QPushButton, QWidget, QFrame

from fk.qt.info_overlay import InfoOverlay, show_info_overlay
from fk.tools.minimal_common import MinimalCommon


def show_popup_once(widget: QWidget):
    show_info_overlay("You can re-enable toolbars in Settings > Appearance",
                       widget.mapToGlobal(widget.rect().center()),
                       ":/icons/info.png",
                       0)


def reset():
    # TODO: Reset settings here
    pass


mc = MinimalCommon(initialize_source=False)
reset()
button = QPushButton(mc.get_window())
button.setFixedWidth(300)
button.setText('Show popup once')
button.clicked.connect(lambda: show_popup_once(button))
mc.get_window().setCentralWidget(button)

mc.main_loop()

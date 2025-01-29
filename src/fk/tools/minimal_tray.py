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
from PySide6.QtWidgets import QPushButton

from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.qt.qt_timer import QtTimer
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer
from fk.qt.tray_icon import TrayIcon
from fk.tools.minimal_common import MinimalCommon

mc = MinimalCommon()

app = mc.get_app()
window = mc.get_window()
actions = mc.get_actions()

pomodoro_timer = PomodoroTimer(QtTimer("Pomodoro Tick"), QtTimer("Pomodoro Transition"), mc.get_settings(), app.get_source_holder())
tray = TrayIcon(window, pomodoro_timer, app.get_source_holder(), actions, 48, MinimalTimerRenderer, True)   # TODO: Detect automatically

tray.setVisible(True)
tray.mode_changed('idle', 'working')
wi = Workitem('Test', '123', None, None)

value = 0
pomodoro_timer._state = 'work'


def tick():
    global value
    global pomodoro_timer
    tray.tick(Pomodoro(False, pomodoro_timer._state, 5000, 5000, POMODORO_TYPE_NORMAL, "123", wi, None),
              'State',
              value,
              10,
              'working')
    value += 1
    if value > 10:
        if pomodoro_timer._state == 'work':
            pomodoro_timer._state = 'rest'
        else:
            pomodoro_timer._state = 'work'
        value = 0


button = QPushButton(window)
button.setText('See tray icon')
button.clicked.connect(lambda: tick())
window.setCentralWidget(button)

mc.main_loop()

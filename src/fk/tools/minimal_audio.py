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

from fk.core.timer import PomodoroTimer
from fk.qt.audio_player import AudioPlayer
from fk.qt.qt_timer import QtTimer
from fk.tools.minimal_common import MinimalCommon

mc = MinimalCommon()

pomodoro_timer = PomodoroTimer(QtTimer("Pomodoro Tick"), QtTimer("Pomodoro Transition"), mc.get_settings(), mc.get_app().get_source_holder())
audio = AudioPlayer(mc.get_window(), mc.get_app().get_source_holder(), mc.get_settings(), pomodoro_timer)

button = QPushButton(mc.get_window())
button.setText('Audio')
mc.get_window().setCentralWidget(button)

mc.main_loop()

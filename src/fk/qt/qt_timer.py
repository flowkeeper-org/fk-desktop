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

from typing import Callable

from PySide6 import QtCore

from fk.core.timer import AbstractTimer


class QtTimer(AbstractTimer):
    _timer: QtCore.QTimer
    _callback: Callable[[dict], None]
    _params: dict | None
    _once: bool

    def __init__(self):
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(lambda: self._call())

    def _call(self) -> None:
        if self._once:
            self._timer.stop()
        self._callback(self._params)

    def schedule(self,
                 ms: float,
                 callback: Callable[[dict], None],
                 params: dict | None,
                 once: bool = False) -> None:
        self._callback = callback
        self._params = params
        self._once = once
        self._timer.start(int(ms))

    def cancel(self):
        self._timer.stop()

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
import datetime
import logging
import threading
from typing import Callable

from PySide6.QtCore import QEvent, QCoreApplication, QTimer

from fk.core.timer import AbstractTimer

logger = logging.getLogger(__name__)


class QExtendedTimer(QTimer):
    def __init__(self):
        super().__init__()

    def customEvent(self, event: QEvent) -> None:
        logger.debug(f'QExtendedTimer - customEvent, {threading.get_ident()}, {self.objectName()}')
        self.start(int(event.ms))

    def schedule_start(self, ms: float) -> None:
        logger.debug(f'QExtendedTimer - scheduling, {threading.get_ident()}, {self.objectName()}')
        # We need to be careful -- this function might be called
        # from a non-GUI thread. We should decouple it via Slots.
        e = QEvent(QEvent.Type.User)
        e.ms = ms
        QCoreApplication.postEvent(self, e)


class QtTimer(AbstractTimer):
    _timer: QExtendedTimer
    _callback: Callable[[dict, datetime.datetime], None]
    _params: dict | None
    _once: bool
    _name: str

    def __init__(self, name: str):
        self._name = name
        logger.debug(f'Creating timer {name}')
        self._timer = QExtendedTimer()
        self._timer.setObjectName(name)
        self._timer.timeout.connect(lambda: self._call())

    def _call(self) -> None:
        if self._once:
            self._timer.stop()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'QtTimer - callback, {threading.get_ident()}, {self._name}')
        self._callback(self._params, datetime.datetime.now(datetime.timezone.utc))

    def schedule(self,
                 ms: float,
                 callback: Callable[[dict, datetime.datetime], None],
                 params: dict | None,
                 once: bool = False) -> None:
        # We need to be careful -- this function might be called
        # from a non-GUI thread. We should decouple it via Slots.
        self._callback = callback
        self._params = params
        self._once = once
        # self._timer.schedule_start(ms)
        self._timer.start(int(ms))

    def cancel(self):
        self._timer.stop()

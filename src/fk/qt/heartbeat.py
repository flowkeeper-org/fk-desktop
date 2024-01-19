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

from fk.core import events
from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.timer import AbstractTimer
from fk.desktop.desktop_strategies import PingStrategy
from fk.qt.qt_timer import QtTimer


class Heartbeat(AbstractEventEmitter):
    _timer: AbstractTimer
    _source: AbstractEventSource
    _state: str
    _last_sent_uid: str
    _last_received_uid: str
    _last_sent_time: datetime.datetime
    _last_received_time: datetime.datetime
    _threshold_ms: int
    _every_ms: int
    _last_ping_ms: int

    def __init__(self, source: AbstractEventSource, every_ms: int, threshold_ms: int):
        AbstractEventEmitter.__init__(self,
                                      [events.WentOnline, events.WentOffline],
                                      source.get_settings().invoke_callback)
        self._source = source
        self._timer = QtTimer('Heartbeat')
        self._state = 'unknown'
        self._last_sent_uid = ''
        self._last_received_uid = ''
        self._last_sent_time = None
        self._last_received_time = None
        self._every_ms = every_ms
        self._threshold_ms = threshold_ms
        self._last_ping_ms = -1
        source.on(events.PongReceived, self._on_pong)
        source.on(events.SourceMessagesRequested, self.start)

    def start(self, event) -> None:
        self._send_ping(None)
        self._timer.schedule(self._every_ms,
                             self._send_ping,
                             None,
                             False)

    def _send_ping(self, params: dict | None) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if self._last_sent_time and not self.is_offline():
            diff_ms = (now - self._last_sent_time).total_seconds() * 1000
            if diff_ms > self._threshold_ms and self._last_received_uid != self._last_sent_uid:
                self._state = 'offline'
                self._emit(events.WentOffline, {
                    'after': diff_ms,
                    'last_received': self._last_received_time,
                })
        self._last_sent_uid = self._source.send_ping()
        self._last_sent_time = now

    def _on_pong(self, event, uid) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        if self._last_sent_uid == uid:
            diff_ms = (now - self._last_sent_time).total_seconds() * 1000
            self._last_ping_ms = diff_ms
            if not self.is_online():
                if diff_ms <= self._threshold_ms:
                    self._state = 'online'
                    self._emit(events.WentOnline, {
                        'ping': diff_ms,
                    })
        else:
            print(f'Warning - received unexpected pong {uid}')
        self._last_received_uid = uid
        self._last_received_time = now

    def stop(self) -> None:
        self._timer.cancel()

    def is_online(self) -> bool:
        return self._state == 'online'

    def is_offline(self) -> bool:
        return self._state == 'offline'

    # This may be -1 if there's been no pong yet
    def get_last_ping(self) -> int:
        return self._last_ping_ms

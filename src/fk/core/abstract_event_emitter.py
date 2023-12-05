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

import re
from abc import ABC
from typing import Callable


class AbstractEventEmitter(ABC):
    _muted: bool
    _connections: dict[str, list[Callable]]

    def __init__(self, allowed_events: list[str]):
        self._muted = False
        self._connections = dict()
        for event in allowed_events:
            self._connections[event] = list[Callable]()

    # Event subscriptions. Here event_pattern can contain * characters
    # and other regex syntax.
    def connect(self, event_pattern: str, callback: Callable) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections:
            if regex.match(event):
                # Ordered set semantics
                if callback not in self._connections[event]:
                    self._connections[event].append(callback)

    def disconnect_all(self, event_pattern: str) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections:
            if regex.match(event):
                self._connections[event].clear()

    def _emit(self, event: str, params: dict[str, any]) -> any:
        if not self._is_muted() or 'MessageProcessed' in event:
            for callback in self._connections[event]:
                params['event'] = event
                res = callback(**params)
                if res:
                    # Abort if we received something non-None
                    return res

    def _is_muted(self) -> bool:
        return self._muted

    def unmute(self) -> None:
        self._muted = False

    def mute(self) -> None:
        self._muted = True

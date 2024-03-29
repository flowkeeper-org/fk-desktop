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
from typing import Callable


class AbstractEventEmitter:
    _muted: bool
    _connections: dict[str, list[Callable]]
    _callback_invoker: Callable

    def __init__(self, allowed_events: list[str], callback_invoker: Callable):
        self._muted = False
        self._callback_invoker = callback_invoker
        self._connections = dict()
        for event in allowed_events:
            self._connections[event] = list[Callable]()

    # Event subscriptions. Here event_pattern can contain * characters
    # and other regex syntax.
    def on(self, event_pattern: str, callback: Callable) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections:
            if regex.match(event):
                # Ordered set semantics
                if callback not in self._connections[event]:
                    print(f'{self.__class__.__name__}.on({event}) from {callback}')
                    self._connections[event].append(callback)

    def cancel(self, event_pattern: str) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections:
            if regex.match(event):
                self._connections[event].clear()

    def _emit(self, event: str, params: dict[str, any], carry: any = None) -> None:
        if not self._is_muted():
            for callback in self._connections[event]:
                params['event'] = event
                if carry is not None:
                    params['carry'] = carry
                self._callback_invoker(callback, **params)
            # print(f'Emitted {self.__class__.__name__} --[{event}]({params})')

    def _is_muted(self) -> bool:
        return self._muted

    def unmute(self) -> None:
        print('Unmuting events')
        self._muted = False

    def mute(self) -> None:
        print('Muting events')
        self._muted = True

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
import inspect
import logging
import re
from typing import Callable

from fk.core.events import register_event

logger = logging.getLogger(__name__)


def _callback_display(callback) -> str:
    if inspect.ismethod(callback):
        return f'{callback.__self__.__class__.__name__}[{id(callback.__self__)}].{callback.__name__}'
    else:
        return f'Function {callback.__name__}'


class AbstractEventEmitter:
    _muted: bool
    _connections_1: dict[str, list[Callable]]
    # UC-2: Certain event consumers can be notified at the end
    _connections_2: dict[str, list[Callable]]
    _last: set[Callable]
    _callback_invoker: Callable

    def __init__(self, allowed_events: list[str], callback_invoker: Callable):
        self._muted = False
        self._callback_invoker = callback_invoker
        self._connections_1 = dict()
        self._connections_2 = dict()
        self._last = set()
        for event in allowed_events:
            self._connections_1[event] = list[Callable]()
            self._connections_2[event] = list[Callable]()
        # We need to do it in the separate loop, because registration might already trigger subscriptions
        for event in allowed_events:
            register_event(event, self)

    # Event subscriptions. Here event_pattern can contain * characters
    # and other regex syntax.
    def on(self, event_pattern: str, callback: Callable, last: bool = False) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections_1:   # _connections_2 has the same list
            if regex.match(event):
                # UC-2: Event consumers are notified in the order of subscription
                if not last and callback not in self._connections_1[event]:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f' # {_callback_display(callback)} subscribed to {self.__class__.__name__}.{event}')
                    self._connections_1[event].append(callback)
                elif last and callback not in self._connections_2[event]:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f' # {_callback_display(callback)} subscribed to {self.__class__.__name__}.{event} as the LAST handler')
                    self._connections_2[event].append(callback)

    def cancel(self, event_pattern: str) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections_1:
            if regex.match(event):
                self._connections_1[event].clear()
                self._connections_2[event].clear()

    def unsubscribe(self, callback: Callable) -> None:
        for callables in self._connections_1.values():
            if callback in callables:
                callables.remove(callback)
        for callables in self._connections_2.values():
            if callback in callables:
                callables.remove(callback)

    def unsubscribe_one(self, callback: Callable, event_pattern: str) -> None:
        regex = re.compile(event_pattern.replace('*', '.*'))
        for event in self._connections_1:
            if regex.match(event):
                if callback in self._connections_1[event]:
                    self._connections_1[event].remove(callback)
                if callback in self._connections_2[event]:
                    self._connections_2[event].remove(callback)

    def _emit(self, event: str, params: dict[str, any], carry: any = None, force: bool = False) -> None:
        if not self._is_muted() or force:
            params['event'] = event
            if carry is not None:
                params['carry'] = carry
            for callback in self._connections_1[event]:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f' ! {_callback_display(callback)}(' + str(params) + ')')
                self._callback_invoker(callback, **params)
            for callback in self._connections_2[event]:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f' ! {_callback_display(callback)}(' + str(params) + ')')
                self._callback_invoker(callback, **params)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(' < ' + self.__class__.__name__ + '._emit(' + event + ')')

    def _is_muted(self) -> bool:
        return self._muted

    def unmute(self) -> None:
        logger.debug('Unmuting events')
        self._muted = False

    def mute(self) -> None:
        logger.debug('Muting events')
        self._muted = True

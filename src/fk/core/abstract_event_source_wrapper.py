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
from __future__ import annotations

import datetime
import logging
from abc import ABC
from typing import TypeVar, Callable, Iterable, Self

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro
from fk.core.user import User
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class AbstractEventSourceWrapper(AbstractEventSource[TRoot], ABC):
    _wrapped: AbstractEventSource[TRoot]

    def __init__(self, wrapped: AbstractEventSource[TRoot]):
        super().__init__(wrapped._serializer, wrapped._settings, wrapped._cryptograph)
        self._wrapped = wrapped

    def start(self, mute_events: bool = True, last_seq: int = 0) -> None:
        self._wrapped.start(mute_events, last_seq)

    def get_data(self) -> TRoot:
        return self._wrapped.get_data()

    def set_data(self, data: TRoot) -> None:
        self._wrapped.set_data(data)

    def get_name(self) -> str:
        return self._wrapped.get_name()

    def append(self, strategies: Iterable[AbstractStrategy]) -> None:
        return self._wrapped.append(strategies)

    def clone(self, new_root: TRoot) -> Self:
        return self._wrapped.clone(new_root)

    def on(self, event_pattern: str, callback: Callable, last: bool = False) -> None:
        self._wrapped.on(event_pattern, callback, last)

    def unsubscribe(self, callback: Callable) -> None:
        self._wrapped.unsubscribe(callback)

    def cancel(self, event_pattern: str) -> None:
        self._wrapped.cancel(event_pattern)

    def unmute(self) -> None:
        self._wrapped.unmute()

    def mute(self) -> None:
        self._wrapped.mute()

    def get_config_parameter(self, name: str) -> str:
        return self._wrapped.get_config_parameter(name)

    def set_config_parameters(self, values: dict[str, str]) -> None:
        return self._wrapped.set_config_parameters(values)

    def execute(self,
                strategy_class:
                type[AbstractStrategy],
                params: list[str],
                persist: bool = True,
                when: datetime.datetime = None,
                auto: bool = False,
                carry: any = None) -> None:
        self._wrapped.execute(strategy_class, params, persist, when, auto, carry)

    def execute_prepared_strategy(self,
                                  strategy: AbstractStrategy[TRoot],
                                  auto: bool = False,
                                  persist: bool = False) -> None:
        self._wrapped.execute_prepared_strategy(strategy, auto, persist)

    def users(self) -> Iterable[User]:
        return self._wrapped.users()

    def backlogs(self) -> Iterable[Backlog]:
        return self._wrapped.backlogs()

    def workitems(self) -> Iterable[Workitem]:
        return self._wrapped.workitems()

    def pomodoros(self) -> Iterable[Pomodoro]:
        return self._wrapped.pomodoros()

    def find_workitem(self, uid: str) -> Workitem | None:
        return self._wrapped.find_workitem(uid)

    def find_backlog(self, uid: str) -> Backlog | None:
        return self._wrapped.find_backlog(uid)

    def find_user(self, identity: str) -> User | None:
        return self._wrapped.find_user(identity)

    def disconnect(self):
        self._wrapped.disconnect()

    def send_ping(self) -> str | None:
        return self._wrapped.send_ping()

    def can_connect(self):
        return self._wrapped.can_connect()

    def repair(self):
        return self._wrapped.repair()

    def compress(self):
        return self._wrapped.compress()

    def get_last_sequence(self):
        return self._wrapped.get_last_sequence()

    def get_init_strategy(self,
                          emit: Callable[[str, dict[str, any], any], None],
                          ) -> AbstractStrategy[AbstractEventSource[TRoot]]:
        return self._wrapped.get_init_strategy(emit)

    def get_id(self) -> str:
        return self._wrapped.get_id()

    def is_online(self) -> bool:
        return self._wrapped.is_online()

    def went_online(self, ping: int = 0) -> None:
        self._wrapped.went_online(ping)

    def went_offline(self, after: int = 0, last_received: datetime.datetime = None) -> None:
        self._wrapped.went_offline(after, last_received)

    def is_online(self) -> bool:
        return self._wrapped.is_online()

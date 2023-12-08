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
from abc import ABC, abstractmethod
from typing import Callable, Type, Self

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.core.user import User


class AbstractStrategy(ABC):
    _seq: int
    _when: datetime.datetime
    _params: list[str]
    _emit: Callable[[str, dict[str, any]], None]
    _users: dict[str, User]
    _settings: AbstractSettings
    _who: User

    # TODO -- Add strategy source, i.e. where it originates from
    # This will allow us have master / slave clients and maintain
    # consistency even if they all go offline and then reconnect
    # (this may happen during the server restarts).
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 users: dict[str, User],
                 settings: AbstractSettings,
                 replacement_user: User | None = None):
        self._seq = seq
        self._when = when
        self._params = params
        self._emit = emit
        self._users = users
        self._settings = settings
        if replacement_user is None:
            if username in users:
                self._who = users[username]
            else:
                raise Exception(f'Unexpected user {username}')
        else:
            self._who = replacement_user

    @staticmethod
    def escape_parameter(value):
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def __str__(self):
        # Escape params
        escaped = [AbstractStrategy.escape_parameter(p) for p in self._params]
        if len(escaped) < 2:
            escaped.append("")
        if len(escaped) < 2:
            escaped.append("")
        params = '"' + '", "'.join(escaped) + '"'
        return f'{self._seq}, {self._when}, {self._who.get_identity()}: {self.get_name()}({params})'

    def get_name(self) -> str:
        name = self.__class__.__name__
        return name[0:len(name) - 8]

    def get_sequence(self) -> int:
        return self._seq

    @abstractmethod
    def execute(self) -> (str, any):
        pass

    def get_params(self):
        return self._params

    def execute_another(self, cls: Type[Self], params: list[str]) -> (str, any):
        strategy = cls(self._seq,
                       self._when,
                       self._who.get_identity(),
                       params,
                       self._emit,
                       self._users,
                       self._settings)
        params = {'strategy': strategy, 'auto': True}
        self._emit(events.BeforeMessageProcessed, params)
        res = strategy.execute()
        self._emit(events.AfterMessageProcessed, params)
        return res

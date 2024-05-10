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
from typing import Callable, Type, Self, Generic, TypeVar

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_data_item import AbstractDataItem
from fk.core.abstract_settings import AbstractSettings
from fk.core.user import User

TRoot = TypeVar('TRoot', bound=AbstractDataItem)


class AbstractStrategy(ABC, Generic[TRoot]):
    _seq: int
    _when: datetime.datetime
    _params: list[str]
    _emit_func: Callable[[str, dict[str, any], any], None]
    _data: TRoot
    _settings: AbstractSettings
    _user: User
    _carry: any

    # TODO -- Add strategy source, i.e. where it originates from
    # This will allow us have master / slave clients and maintain
    # consistency even if they all go offline and then reconnect
    # (this may happen during the server restarts).
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: TRoot,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 carry: any = None):
        self._seq = seq
        self._when = when
        self._user = user
        self._params = params
        self._emit_func = emit
        self._data = data
        self._settings = settings
        self._carry = carry

    @abstractmethod
    def get_encrypted_parameters(self) -> list[str]:
        return self._params

    @staticmethod
    @abstractmethod
    def decrypt_parameters(params: list[str]) -> list[str]:
        return params

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
        return f'{self._seq}, {self._when}, {self._user.get_identity()}: {self.get_name()}({params})'

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
                       self._user,
                       params,
                       self._emit_func,
                       self._data,
                       self._settings)
        params = {'strategy': strategy, 'auto': True}
        self._emit(events.BeforeMessageProcessed, params)
        res = strategy.execute()
        self._emit(events.AfterMessageProcessed, params)
        return res

    def _emit(self, name: str, params: dict[str, any]):
        self._emit_func(name, params, self._carry)

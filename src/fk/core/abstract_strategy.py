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
from fk.core.abstract_data_item import AbstractDataItem
from fk.core.abstract_settings import AbstractSettings

TRoot = TypeVar('TRoot', bound=AbstractDataItem)


class AbstractStrategy(ABC, Generic[TRoot]):
    _seq: int
    _when: datetime.datetime
    _params: list[str]
    _settings: AbstractSettings
    _user_identity: str
    _carry: any

    # TODO -- Add strategy source, i.e. where it originates from
    # This will allow us have master / slave clients and maintain
    # consistency even if they all go offline and then reconnect
    # (this may happen during the server restarts).
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        self._seq = seq
        self._when = when
        self._user_identity = user_identity
        self._params = params
        self._settings = settings
        self._carry = carry

    def get_name(self) -> str:
        name = self.__class__.__name__
        return name[0:len(name) - 8]

    def get_when(self) -> datetime.datetime:
        return self._when

    def get_user_identity(self) -> str:
        return self._user_identity

    def replace_user_identity(self, user_identity: str) -> None:
        self._user_identity = user_identity

    def get_sequence(self) -> int:
        return self._seq

    def encryptable(self) -> bool:
        return True

    @abstractmethod
    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: TRoot) -> (str, any):
        pass

    def get_params(self):
        return self._params

    def execute_another(self,
                        emit: Callable[[str, dict[str, any], any], None],
                        data: TRoot,
                        cls: Type[Self],
                        params: list[str]) -> (str, any):
        strategy = cls(self._seq,
                       self._when,
                       self._user_identity,
                       params,
                       self._settings)
        params = {'strategy': strategy, 'auto': True}
        emit(events.BeforeMessageProcessed, params, self._carry)
        res = strategy.execute(emit, data)
        emit(events.AfterMessageProcessed, params, self._carry)
        return res

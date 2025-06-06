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
from abc import ABC, abstractmethod
from typing import Callable, Type, Generic, TypeVar

from fk.core import events
from fk.core.abstract_data_item import AbstractDataItem
from fk.core.abstract_settings import AbstractSettings
from fk.core.tenant import Tenant
from fk.core.user import User

TRoot = TypeVar('TRoot', bound=AbstractDataItem)


class AbstractStrategy(ABC, Generic[TRoot]):
    _seq: int
    _when: datetime.datetime
    _params: list[str]
    _settings: AbstractSettings
    _user_identity: str
    _carry: any

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
        # UC-3: Strategy names correspond to Python class names without trailing "...Strategy"
        return name[0:len(name) - 8]

    def get_when(self) -> datetime.datetime:
        return self._when

    def get_user_identity(self) -> str:
        return self._user_identity

    def replace_user_identity(self, user_identity: str) -> None:
        self._user_identity = user_identity

    def get_sequence(self) -> int:
        return self._seq

    def update_sequence(self, new_seq: int) -> None:
        self._seq = new_seq

    def encryptable(self) -> bool:
        # UC-3: All strategies should be e2e-encrypted by default
        return True

    def requires_sealing(self) -> bool:
        # UC-3: Strategies don't require auto-sealing by default
        return False

    @abstractmethod
    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: TRoot) -> None:
        pass

    def get_params(self):
        return self._params

    # This is for "auto-executed" strategies only. Those won't be persisted. It doesn't support auto-sealing, but
    # that's OK since it is always called in the context of another strategy, which was auto-sealed.
    def execute_another(self,
                        emit: Callable[[str, dict[str, any], any], None],
                        data: TRoot,
                        cls: Type[AbstractStrategy[TRoot]],
                        params: list[str],
                        when_override: datetime.datetime | None = None,
                        user_override: str | None = None) -> None:
        strategy = cls(self._seq,
                       self._when if when_override is None else when_override,
                       self._user_identity if user_override is None else user_override,
                       params,
                       self._settings)
        params = {
            'strategy': strategy,
            'auto': True,
            'persist': False,
        }
        emit(events.BeforeMessageProcessed, params, self._carry)
        strategy.execute(emit, data)
        emit(events.AfterMessageProcessed, params, self._carry)

    # Convenience methods

    def get_user(self, data: Tenant, fail_if_not_found: bool = True) -> User | None:
        if self._user_identity in data:
            return data.get_user(self._user_identity)

        if fail_if_not_found:
            raise Exception(f'User "{self._user_identity}" not found')
        else:
            return None

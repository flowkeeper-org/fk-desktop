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
from typing import Callable

from fk.core.abstract_settings import AbstractSettings, S
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant


# Configure("1", "123-456-789")
@strategy
class ConfigureStrategy(AbstractStrategy[Tenant]):
    _version: str
    _salt: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: str = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._version = params[0]
        self._salt = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        self._settings.set({
            S.SOURCE_ENCRYPTION_SALT: self._salt,
            S.SOURCE_VERSION: self._version,
        })

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
import re
from typing import Callable

from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.strategy_factory import strategy
from fk.core.user import User

EMAIL_REGEX = re.compile(r'[\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4}')


# Authenticate("alice@example.com", "secret")
@strategy
class AuthenticateStrategy(AbstractStrategy['App']):
    _username: str
    _token: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 data: 'App',
                 settings: AbstractSettings):
        super().__init__(seq, when, user, params, emit, data, settings)
        self._username = params[0]
        self._token = params[1]

    def execute(self) -> (str, any):
        return None, None


# Replay("105")
@strategy
class ReplayStrategy(AbstractStrategy):
    _since_seq: int

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 data: 'App',
                 settings: AbstractSettings):
        super().__init__(seq, when, user, params, emit, data, settings)
        self._since_seq = int(params[0])

    def execute(self) -> (str, any):
        return None, None

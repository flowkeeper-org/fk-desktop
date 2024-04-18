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

from PySide6.QtWidgets import QMessageBox

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.strategy_factory import strategy
from fk.core.user import User

EMAIL_REGEX = re.compile(r'[\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4}')


# Authenticate("alice@example.com", "secret")
@strategy
class AuthenticateStrategy(AbstractStrategy['Tenant']):
    _username: str
    _token: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
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
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._since_seq = int(params[0])

    def execute(self) -> (str, any):
        # Send only
        return None, None


# Error("401", "User not found")
@strategy
class ErrorStrategy(AbstractStrategy):
    _error_code: int
    _error_message: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._error_code = int(params[0])
        self._error_message = params[1]

    def execute(self) -> (str, any):
        if self._error_message == 'User consent is required':
            QMessageBox().warning(
                None,
                "IMPORTANT",
                "Flowkeeper.org is in its BETA testing stage. It lacks end-to-end encryption, which means "
                "that our engineers have access to your data. DO NOT STORE ANY SENSITIVE INFORMATION IN "
                "FLOWKEEPER.ORG -- we may read it or it may disappear at any time.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        else:
            raise Exception(self._error_message)


# Pong("123-456-789-012", "")
@strategy
class PongStrategy(AbstractStrategy):
    _uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 data: 'System',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._uid = params[0]

    def execute(self) -> (str, any):
        # print(f'Received Pong - {self._uid}')
        self._emit(events.PongReceived, {
            'uid': self._uid
        })
        return None, None


# Ping("123-456-789-012", "")
@strategy
class PingStrategy(AbstractStrategy):
    _uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._uid = params[0]

    def execute(self) -> (str, any):
        # Send only
        return None, None

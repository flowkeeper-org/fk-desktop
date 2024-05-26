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
from fk.core.tenant import Tenant

EMAIL_REGEX = re.compile(r'[\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4}')


# Authenticate("alice@example.com", "google|token123", "false")
@strategy
class AuthenticateStrategy(AbstractStrategy[Tenant]):
    last_username: str = ''
    last_token: str = ''

    _username: str
    _token: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._username = params[0]
        self._token = params[1]

    def encryptable(self) -> bool:
        return False

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        # Those are used in the scenario when the server requests user's consent before creating new account
        AuthenticateStrategy.last_username = self._username
        AuthenticateStrategy.last_token = self._token
        return None, None


# Replay("105")
@strategy
class ReplayStrategy(AbstractStrategy):
    _since_seq: int

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._since_seq = int(params[0])

    def encryptable(self) -> bool:
        return False

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
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
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._error_code = int(params[0])
        self._error_message = params[1]

    def encryptable(self) -> bool:
        return False

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        if self._error_message == 'User consent is required':
            if QMessageBox().warning(
                None,
                "IMPORTANT",
                "Support for Flowkeeper Server is experimental. We host Flowkeeper.org on best-effort basis and "
                "we cannot guarantee 24/7 reliable uptime. We may accidentally lose your data or terminate our"
                "service without warning. Your data is encrypted and decrypted on your computer, so we don't "
                "have access to its content. If you click Yes, we will automatically create an account for the"
                "email you provided, and won't show this message again. If you'd like to delete your account, "
                "please send an email to contact@flowkeeper.org.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                print('Will execute Authenticate with true')

                self.execute_another(emit,
                                     data,
                                     AuthenticateStrategy,
                                     [AuthenticateStrategy.last_username, AuthenticateStrategy.last_token, 'true'])
        else:
            raise Exception(self._error_message)


# Pong("123-456-789-012", "")
@strategy
class PongStrategy(AbstractStrategy):
    _uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._uid = params[0]

    def encryptable(self) -> bool:
        return False

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        # print(f'Received Pong - {self._uid}')
        emit(events.PongReceived, {
            'uid': self._uid
        }, self._carry)
        return None, None


# Ping("123-456-789-012", "")
@strategy
class PingStrategy(AbstractStrategy):
    _uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._uid = params[0]

    def encryptable(self) -> bool:
        return False

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        # Send only
        return None, None

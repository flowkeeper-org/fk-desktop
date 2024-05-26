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
            # TODO: Transfer this message from the server
            if QMessageBox().warning(
                None,
                "Do you want to create an account?",
                "PLEASE READ IT: Support for Flowkeeper Server is experimental. We host Flowkeeper.org on "
                "best-effort basis and deploy updates frequently, all of which means that in general we cannot "
                "provide reliable 24/7 service. Unplanned downtime should be expected and WILL happen. \n\n"
                "RELIABILITY: Although we take regular backups and handle your data as carefully as we can, we "
                "cannot guarantee that your data will be stored forever. We may accidentally lose it or simply "
                "terminate our service without warning. We recommend you to export your data to a local backup "
                "file from time to time. \n\n"
                "SECURITY: Your data is encrypted and decrypted on your computer using Fernet algorithm, "
                "which is based on AES cypher. The server deals with encrypted content only, and we don't "
                "have any means of decrypting it, so as long as you keep your encryption key private, your "
                "personal data should be safe.\n\n"
                "If you click Yes, we will automatically create an account for the "
                "email you provided, and won't show this message again. If you'd like to "
                "delete your account, please send an email to contact@flowkeeper.org.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                print('Obtained consent for Flowkeeper Server, will re-authenticate')
                # TODO: Recreate the source. This will trigger re-authentication, this time with
                #  "true" parameter, meaning that the user has already given their consent.
                self._settings.set({
                    'WebsocketEventSource.consent': 'True',
                })
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

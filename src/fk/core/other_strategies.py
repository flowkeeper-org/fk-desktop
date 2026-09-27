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
import base64
import datetime
from typing import Callable

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from fk.core.abstract_settings import AbstractSettings, S
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant


# Configure("2", "123-456-789", "<encrypted text>")
@strategy
class ConfigureStrategy(AbstractStrategy[Tenant]):
    _version: str
    _salt: str
    _check: str

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
        self._check = params[2]

    def get_version(self):
        return self._version

    def get_salt(self):
        return self._salt

    def get_check(self):
        return self._check

    def is_valid(self):
        key = self._settings.get(S.SOURCE_ENCRYPTION_KEY)
        check = FernetCryptograph.encrypt_check(key, self._salt)
        return check == self._check

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        if self._carry != 'init':
            # TODO: Storing it as settings is an undesirable side effect.
            self._settings.set({
                S.SOURCE_ENCRYPTION_SALT: self._salt,
                S.SOURCE_VERSION: self._version,
            })

            if not self.is_valid():
                raise Exception(f'Cannot decrypt data, invalid end-to-end encryption key')

    def encryptable(self) -> bool:
        return False

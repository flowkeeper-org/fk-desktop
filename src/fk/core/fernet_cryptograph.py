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
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings, S

logger = logging.getLogger(__name__)


class FernetCryptograph(AbstractCryptograph):
    _fernet: Fernet | None

    def __init__(self, settings: AbstractSettings):
        self._fernet = None
        super().__init__(settings)
        # UC-2: The "final" e2e encryption key is cached in the keychain
        cached_key = self._settings.get(S.SOURCE_ENCRYPTION_KEY_CACHE)
        if self._fernet is None:
            # It might've been created as part of the super() constructor, which triggered our _on_key_changed()
            self._fernet = self._create_fernet(cached_key)

    def _create_fernet(self, cached_key) -> Fernet:
        if cached_key is None or cached_key == '':
            logger.debug(f'Creating Fernet cryptograph using salt {self.salt}')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=bytes.fromhex(self.salt),
                iterations=600000, # See https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.key.encode('utf-8')))
            self._settings.set({S.SOURCE_ENCRYPTION_KEY_CACHE: key.decode('utf-8')})
        else:
            logger.debug(f'Creating Fernet cryptograph from a cached key')
            key = cached_key.encode('utf-8')

        logger.debug(f'Fernet encryption key: {"*" * len(key)}')
        return Fernet(key)

    def _on_key_changed(self) -> None:
        self._fernet = self._create_fernet('')

    def encrypt(self, s: str) -> str:
        return self._fernet.encrypt(
            s.encode('utf-8')
        ).decode('utf-8')

    def decrypt(self, s: str) -> str:
        return self._fernet.decrypt(
            s.encode('utf-8')
        ).decode('utf-8')

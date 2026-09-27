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
import json
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings, S

logger = logging.getLogger(__name__)


class FernetCryptograph(AbstractCryptograph):
    _fernets: dict[str, Fernet]
    _current_fernet_id: str

    def __init__(self, settings: AbstractSettings):
        super().__init__(settings)
        self._current_fernet_id = ''
        self._fernets = dict()
        self._on_key_changed()

    @staticmethod
    def _get_key(key: str, salt: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=bytes.fromhex(salt),
            iterations=600000,  # See https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
        )
        return base64.urlsafe_b64encode(kdf.derive(key.encode('utf-8')))

    def _get_fernet(self, fernet_id) -> Fernet:
        # First, try to find it in the settings cache
        keys_cache_str = self._settings.get(S.SOURCE_ENCRYPTION_KEYS_CACHE)
        keys_cache = json.loads(keys_cache_str)

        if fernet_id in keys_cache:
            logger.debug(f'Creating Fernet cryptograph from a cached key')
            cached_key = keys_cache[fernet_id]
            return Fernet(cached_key.encode('utf-8'))
        else:
            logger.debug(f'Creating Fernet cryptograph using salt {self.salt} and key {"*" * len(self.key)}')
            key = FernetCryptograph._get_key(self.key, self.salt)

            # Save it in the keyring
            keys_cache[fernet_id] = key.decode('utf-8')
            self._settings.set({S.SOURCE_ENCRYPTION_KEYS_CACHE: json.dumps(keys_cache)})

            return Fernet(key)

    def _on_key_changed(self) -> None:
        # We lazy-create Fernet objects when we need to encrypt or decrypt data. Here we only
        # precalculate fernet_id, so that we don't need to compute key and salt hashes for
        # each (en|de)crypt operation.
        if self.key and self.salt:
            self._current_fernet_id = hash(self.key) + hash(self.salt)
            logger.debug(f'Updated current Fernet ID: {self._current_fernet_id}')

    def _encrypt_or_decrypt(self, s: str, is_encrypt: bool) -> str:
        if self.enabled:
            if not self.key:
                raise Exception(f'Cannot {"encrypt" if is_encrypt else "decrypt"} data without a key.')
            if not self.salt:
                raise Exception(f'Cannot {"encrypt" if is_encrypt else "decrypt"} data without a salt.')
            if not self._current_fernet_id:
                raise Exception(f'Trying to {"encrypt" if is_encrypt else "decrypt"} data before Fernet ID is calculated.')

            fernet: Fernet = self._fernets.get(self._current_fernet_id)
            if not fernet:
                fernet = self._get_fernet(self._current_fernet_id)
                self._fernets[self._current_fernet_id] = fernet
            return (fernet.encrypt if is_encrypt else fernet.decrypt)(
                s.encode('utf-8')
            ).decode('utf-8')
        else:
            return s

    def encrypt(self, s: str) -> str:
        return self._encrypt_or_decrypt(s, True)

    def decrypt(self, s: str) -> str:
        return self._encrypt_or_decrypt(s, False)

    @staticmethod
    def encrypt_check(key: str, salt: str) -> str:
        fernet = Fernet(FernetCryptograph._get_key(key, salt))
        return fernet.encrypt(b'check').decode('utf-8')

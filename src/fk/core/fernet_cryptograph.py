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
from fk.core.abstract_settings import AbstractSettings

logger = logging.getLogger(__name__)


class FernetCryptograph(AbstractCryptograph):
    _fernet: Fernet

    def __init__(self, settings: AbstractSettings):
        super().__init__(settings)
        cached_key = self._settings.get('Source.encryption_key_cache!')
        self._fernet = self._create_fernet(cached_key)

    def _create_fernet(self, cached_key) -> Fernet:
        if cached_key is None or cached_key == '':
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'e1a7a49b5bad75ec81fcb8cded4bbc0c',
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.key.encode('utf-8')))
            self._settings.set({'Source.encryption_key_cache!': key.decode('utf-8')})
        else:
            key = cached_key.encode('utf-8')
        logger.debug(f'Fernet encryption key: {key}')
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

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

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings


class FernetCryptograph(AbstractCryptograph):
    _fernet: Fernet

    def __init__(self, settings: AbstractSettings):
        super().__init__(settings)
        self._on_key_changed()

    def _create_fernet(self) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'e1a7a49b5bad75ec81fcb8cded4bbc0c',
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.key.encode('utf-8')))
        return Fernet(key)

    def _on_key_changed(self) -> None:
        if self.enabled:
            self._fernet = self._create_fernet()
        else:
            self._fernet = None

    def encrypt(self, s: str) -> str:
        if self._fernet is None:
            return s
        return self._fernet.encrypt(
            bytes(s, encoding='utf-8')
        ).decode('utf-8')

    def decrypt(self, s: str) -> str:
        if self._fernet is None:
            return s
        return self._fernet.decrypt(
            s.encode('utf-8')
        ).decode('utf-8')

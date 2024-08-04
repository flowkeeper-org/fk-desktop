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
import secrets
import string
from abc import ABC, abstractmethod

from fk.core.abstract_settings import AbstractSettings
from fk.core.events import AfterSettingsChanged


class AbstractCryptograph(ABC):
    _settings: AbstractSettings
    key: str
    enabled: bool

    def __init__(self, settings: AbstractSettings):
        self._settings = settings
        self.key = self._settings.get('Source.encryption_key!')
        self.enabled = self._settings.is_e2e_encryption_enabled()
        settings.on(AfterSettingsChanged, self._on_setting_changed)
        if settings.get('Source.encryption_key!') == '':
            self._generate_key()

    def _generate_key(self) -> None:
        # UC: Launching FK for the first time, a random e2e encryption key is generated
        key = ''.join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(20)
        )
        self._settings.set({'Source.encryption_key!': key})

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        self.enabled = self._settings.is_e2e_encryption_enabled()
        if 'Source.encryption_key!' in new_values:
            self.key = new_values['Source.encryption_key!']
            self._on_key_changed()

    @abstractmethod
    def _on_key_changed(self) -> None:
        pass

    @abstractmethod
    def encrypt(self, s: str) -> str:
        pass

    @abstractmethod
    def decrypt(self, s: str) -> str:
        pass

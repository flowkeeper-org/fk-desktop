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
from abc import ABC, abstractmethod

from fk.core.abstract_settings import AbstractSettings


class AbstractCryptograph(ABC):
    _settings: AbstractSettings
    key: str
    enabled: bool

    def __init__(self, settings: AbstractSettings):
        self._settings = settings
        self.key = self._settings.get('Source.encryption_key!')
        self.enabled = self._settings.is_e2e_encryption_enabled()

    @abstractmethod
    def _on_key_changed(self) -> None:
        pass

    @abstractmethod
    def encrypt(self, s: str) -> str:
        pass

    @abstractmethod
    def decrypt(self, s: str) -> str:
        pass

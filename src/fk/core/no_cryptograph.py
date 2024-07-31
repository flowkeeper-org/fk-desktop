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
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings


class NoCryptograph(AbstractCryptograph):
    def __init__(self, settings: AbstractSettings):
        # We don't call super() on purpose here, so that it doesn't try to generate keys
        self._settings = settings
        self.enabled = False

    def _on_key_changed(self) -> None:
        self.enabled = False

    def encrypt(self, s: str) -> str:
        return s

    def decrypt(self, s: str) -> str:
        return s

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

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_settings import AbstractSettings
from fk.core.user import User

ADMIN_USER = 'admin@local.host'


class Tenant(AbstractDataContainer[User, None]):
    """Tenant is the root of the data hierarchy in Flowkeeper Client.
    It contains users and has no parent."""

    _settings: AbstractSettings

    def __init__(self, settings: AbstractSettings):
        super().__init__('Flowkeeper Desktop Client',
                         None,
                         '0',
                         datetime.datetime.now(datetime.timezone.utc))
        self._settings = settings
        self[ADMIN_USER] = User(
            self,
            ADMIN_USER,
            'System',
            datetime.datetime.now(datetime.timezone.utc),
            True
        )

    def get_settings(self) -> AbstractSettings:
        return self._settings

    def get_user(self, identity: str) -> User:
        return self[identity]

    def get_current_user(self) -> User:
        return self[self._settings.get_username()]

    def __getstate__(self):
        # Don't pickle the settings
        d = self.__dict__.copy()
        del d['_settings']
        return d

    def __setstate__(self, d):
        d['_settings'] = None
        self.__dict__ = d

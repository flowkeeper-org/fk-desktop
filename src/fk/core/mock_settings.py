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

from fk.core import events
from fk.core.abstract_settings import AbstractSettings


def invoke_direct(fn, **kwargs):
    fn(**kwargs)


class MockSettings(AbstractSettings):
    def __init__(self, filename=None, username=None):
        super().__init__('Arial', 10, invoke_direct)
        self._settings = {
            'FileEventSource.filename': filename,
            'WebsocketEventSource.username': username,
        }

    def get(self, name: str) -> str:
        if name in self._settings:
            return self._settings[name]
        else:
            return self._defaults[name]

    def set(self, name: str, value: str) -> str:
        params = {
            'name': name,
            'old_value': self.get(name) if name in self._settings else None,
            'new_value': value,
        }
        self._emit(events.BeforeSettingChanged, params)
        self._settings[name] = value
        self._emit(events.AfterSettingChanged, params)
        return value

    def location(self) -> str:
        return "N/A"

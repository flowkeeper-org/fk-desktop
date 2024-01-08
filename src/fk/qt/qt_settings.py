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

from PySide6 import QtCore
from PySide6.QtGui import QFont

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_invoker import invoke_in_main_thread


class QtSettings(AbstractSettings):
    _settings: QtCore.QSettings

    def __init__(self):
        font = QFont()
        super().__init__(font.family(), font.pointSize(), invoke_in_main_thread)
        self._settings = QtCore.QSettings("flowkeeper", "desktop-client")

    def set(self, name: str, value: str) -> str:
        params = {
            'name': name,
            'old_value': self.get(name),
            'new_value': value,
        }
        self._emit(events.BeforeSettingChanged, params)
        self._settings.setValue(name, value)
        self._emit(events.AfterSettingChanged, params)
        return value

    def get(self, name: str) -> str:
        return str(self._settings.value(name, self._defaults[name]))

    def location(self) -> str:
        return self._settings.fileName()

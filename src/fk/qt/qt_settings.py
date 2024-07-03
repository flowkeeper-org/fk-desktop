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
import keyring
from PySide6 import QtCore
from PySide6.QtGui import QFont

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_invoker import invoke_in_main_thread


class QtSettings(AbstractSettings):
    _settings: QtCore.QSettings
    _app_name: str

    def __init__(self, app_name: str = 'flowkeeper-desktop'):
        font = QFont()
        self._app_name = app_name
        super().__init__(font.family(), font.pointSize(), invoke_in_main_thread)
        self._settings = QtCore.QSettings("flowkeeper", app_name)

    def set(self, values: dict[str, str]) -> None:
        old_values: dict[str, str] = dict()
        for name in values.keys():
            old_value = self.get(name)
            if old_value != values[name]:
                old_values[name] = old_value
        if len(old_values.keys()) > 0:
            params = {
                'old_values': old_values,
                'new_values': values,
            }
            self._emit(events.BeforeSettingsChanged, params)
            for name in old_values.keys():  # This is not a typo, we've just filtered this list
                # to only contain settings which actually changed.
                if name.endswith('!'):
                    keyring.set_password(self._app_name, name, values[name])
                else:
                    self._settings.setValue(name, values[name])
            self._emit(events.AfterSettingsChanged, params)

    def get(self, name: str) -> str:
        if name.endswith('!'):
            value = keyring.get_password(self._app_name, name)
            return value if value is not None else ''
        else:
            return str(self._settings.value(name, self._defaults[name]))

    def location(self) -> str:
        return self._settings.fileName()

    def clear(self) -> None:
        self._settings.clear()
        for category in self._definitions.values():
            for setting in category:
                key = setting[0]
                if key.endswith('!'):
                    value = keyring.get_password(self._app_name, key)
                    if value is not None:
                        try:
                            keyring.delete_password(self._app_name, key)
                        except Exception as e:
                            # Ignore, this is a common issue with keyring module
                            # It seems to be solved in a more recent version, which doesn't work for us
                            pass

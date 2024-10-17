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
import json
import logging
import sys

import keyring
from PySide6 import QtCore
from PySide6.QtGui import QFont, Qt, QGuiApplication
from PySide6.QtWidgets import QMessageBox, QApplication

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_invoker import invoke_in_main_thread

SECRET_NAME = 'all-secrets'
logger = logging.getLogger(__name__)


def _check_keyring() -> bool:
    return not isinstance(keyring.get_keyring(), keyring.backends.fail.Keyring)


class QtSettings(AbstractSettings):
    _settings: QtCore.QSettings
    _app_name: str
    _keyring_enabled: bool

    def __init__(self, app_name: str = 'flowkeeper-desktop'):
        font = QFont()
        self._app_name = app_name
        super().__init__(font.family(),
                         font.pointSize(),
                         invoke_in_main_thread,
                         QGuiApplication.platformName() == 'wayland')
        self._settings = QtCore.QSettings("flowkeeper", app_name)

        keyring_feature_enabled = self.get('Application.feature_keyring') == 'True'
        self._keyring_enabled = keyring_feature_enabled and _check_keyring()

        if keyring_feature_enabled and not self._keyring_enabled:
            # Display the warning only if keyring check failed
            self._display_warning_if_needed()

        if not self._keyring_enabled:
            self._disable_connected_sources()  # Disable and hide forbidden source types
            self._disable_secrets()  # Disable and hide forbidden encryption settings

        connect_feature_enabled = self.get('Application.feature_connect') == 'True'
        if not connect_feature_enabled:
            self._disable_connected_sources()

    def _display_warning_if_needed(self) -> None:
        if self.get('Application.ignore_keyring_errors') == 'False':
            if QMessageBox().warning(
                    None,
                    "No keyring",
                    "Flowkeeper couldn't detect a compatible keyring for storing credentials. You can try to install one "
                    "(for example, on Kubuntu 20.04, this can be fixed by installing gnome-keyring), or ignore this "
                    "warning. If you choose to ignore it, the following features will be disabled:\n\n"
                    "1. Data sync with flowkeeper.org,\n"
                    "2. Data sync with custom Flowkeeper Server,\n"
                    "3. End-to-end data encryption.",
                    QMessageBox.StandardButton.Ignore | QMessageBox.StandardButton.Abort
            ) == QMessageBox.StandardButton.Ignore:
                logger.debug('Compatible keyring is not found and the user chose to ignore it. '
                             'Encryption and websockets will be disabled.')
                self.set({'Application.ignore_keyring_errors': 'True'})
            else:
                logger.error('Compatible keyring is not found and the user chose not to ignore it. Exiting.')
                sys.exit(1)

    def _disable_connected_sources(self) -> None:
        if self.is_remote_source():
            self.set({'Source.type': 'local'})

        original = self.get_configuration('Source.type')
        for option in list(original):
            key = option.split(':')[0]
            if key in ['flowkeeper.org', 'flowkeeper.pro', 'websocket']:
                original.remove(option)

    def _disable_secrets(self) -> None:
        if self.get('Source.encryption_enabled') == 'True':
            self.set({'Source.encryption_enabled': 'False'})

        # TODO: Reimplement this via some bool variable on the AbstractSettings class, e.g. "is_encryption_disabled"
        #  and updating the corresponding visibility checks. This would be a more elegant solution.
        self.hide('Source.encryption_enabled')
        self.hide('Source.encryption_key!')
        self.hide('Source.encryption_separator')

    def set(self, values: dict[str, str], force_fire=False) -> None:
        old_values: dict[str, str] = dict()
        for name in values.keys():
            old_value = self.get(name)
            if old_value != values[name] or force_fire:
                old_values[name] = old_value
        if len(old_values.keys()) > 0:
            params = {
                'old_values': old_values,
                'new_values': values,
            }
            self._emit(events.BeforeSettingsChanged, params)
            encrypted = dict()
            for name in old_values.keys():  # This is not a typo, we've just filtered this list
                # to only contain settings which actually changed.
                if name.endswith('!'):
                    # We want to set all secrets at once (see explanation below in get())
                    encrypted[name] = values[name]
                else:
                    self._settings.setValue(name, values[name])
            if len(encrypted) > 0:
                if self._keyring_enabled:
                    existing = self.load_secret()
                    for e in encrypted:
                        existing[e] = encrypted[e]
                    keyring.set_password(self._app_name, SECRET_NAME, json.dumps(existing))
                else:
                    logger.warning(f'Setting encrypted preferences {encrypted.keys()}, while the keyring is disabled')
            self._emit(events.AfterSettingsChanged, params)

    def load_secret(self) -> dict[str, str]:
        json_str = keyring.get_password(self._app_name, SECRET_NAME)
        return json.loads(json_str) if json_str else dict()

    def get(self, name: str) -> str:
        if name.endswith('!'):
            if self._keyring_enabled:
                # MacOS keeps asking to unlock login keychain *for each* password. I couldn't find how to avoid
                # this, and decided to squeeze *all* passwords into a single JSON secret instead.
                j = self.load_secret()
                if name in j and j[name] is not None:
                    return j[name]
                else:
                    return ''
            else:
                return self._defaults[name]
        else:
            return str(self._settings.value(name, self._defaults[name]))

    def location(self) -> str:
        return self._settings.fileName()

    def clear(self) -> None:
        self._settings.clear()
        try:
            keyring.delete_password(self._app_name, SECRET_NAME)
        except Exception as e:
            # Ignore, this is a common issue with keyring module.
            pass

    def is_keyring_enabled(self) -> bool:
        return self._keyring_enabled

    def get_auto_theme(self) -> str:
        scheme = QApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return 'dark'
        else:
            return 'mixed'

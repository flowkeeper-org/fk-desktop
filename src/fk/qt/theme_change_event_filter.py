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
import logging

from PySide6.QtCore import QObject, QEvent
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QMainWindow, QApplication

from fk.core.abstract_settings import AbstractSettings

logger = logging.getLogger(__name__)


class ThemeChangeEventFilter(QMainWindow):
    _window: QMainWindow
    _settings: AbstractSettings

    # We need to use it, because Windows sometimes triggers dozens of ThemeChange events at once, and
    #  we don't want to translate all of them into our settings change events, which might be too slow.
    _last_value: Qt.ColorScheme

    def __init__(self,
                 window: QMainWindow,
                 settings: AbstractSettings):
        super().__init__()
        self._window = window
        self._settings = settings
        self._last_value = QApplication.styleHints().colorScheme()

    def eventFilter(self, widget: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ThemeChange:
            if widget == self._window:
                new_theme = QApplication.styleHints().colorScheme()
                logger.debug(f'Theme changed from {self._last_value} to {new_theme}')
                if new_theme != self._last_value:
                    self._settings.set({
                        'Application.theme': 'auto'
                    }, force_fire=True)
                    self._last_value = new_theme
        return False

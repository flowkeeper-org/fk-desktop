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

from fk.core import events
from fk.core.abstract_settings import AbstractSettings

logger = logging.getLogger(__name__)


def invoke_direct(fn, **kwargs):
    fn(**kwargs)


class MockSettings(AbstractSettings):
    _settings: dict[str, str]

    def __init__(self, filename=None, username=None, source_type="local"):
        super().__init__('Arial', 10, invoke_direct)
        self._settings = {
            'Source.type': source_type,
            'FileEventSource.filename': filename,
            'WebsocketEventSource.username': username,
            'Source.encryption_enabled': 'False',
            'Source.encryption_key': 'oBokryM75NwBXkKVa3bY',
            'Source.encryption_key_cache': '_pQAnZe3fKCdq-kLNuoYAq5uUxe-Rb1-8C_vYqN0oyw=',
        }

    def get(self, name: str) -> str:
        if name in self._settings:
            return self._settings[name]
        else:
            return self._defaults[name]

    def set(self, values: dict[str, str]) -> None:
        old_values: dict[str, str] = dict()
        for name in values.keys():
            old_value = self.get(name) if name in self._settings else None
            if old_value != values[name]:
                old_values[name] = old_value
        params = {
            'old_values': old_values,
            'new_values': values,
        }
        self._emit(events.BeforeSettingsChanged, params, None)
        for name in old_values.keys():  # This is not a typo, we've just filtered this list
            # to only contain settings which actually changed.
            self._settings[name] = values[name]
        self._emit(events.AfterSettingsChanged, params, None)

    def location(self) -> str:
        return "N/A"

    def clear(self) -> None:
        self._settings = {}

    def get_displayed_settings(self) -> list[str]:
        res = list()
        for tab_name in self.get_categories():
            logger.debug(f'Category: {tab_name}')
            settings = self.get_settings(tab_name)
            values = dict()
            for s in settings:
                values[s[0]] = s[3]
            for option_id, option_type, option_display, option_value, option_options, option_visible in settings:
                if option_visible(values) and option_type not in ('separator', 'button'):
                    logger.debug(f' - {option_display}: {option_value}')
                    res.append(option_id)
        return res

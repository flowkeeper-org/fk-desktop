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
from typing import Iterable

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter


class AbstractSettings(AbstractEventEmitter, ABC):
    # Category -> [(id, type, display, default, options)]
    _definitions: dict[str, list[tuple[str, str, str, str, list[any]]]]
    _defaults: dict[str, str]

    def __init__(self):
        AbstractEventEmitter.__init__(self, [
            events.BeforeSettingChanged,
            events.AfterSettingChanged,
        ])

        self._definitions = {
            'General': [
                ('Pomodoro.default_work_duration', 'int', 'Default work duration (s)', str(25 * 60), [1, 120 * 60]),
                ('Pomodoro.default_rest_duration', 'int', 'Default rest duration (s)', str(5 * 60), [1, 60 * 60]),
                ('Pomodoro.auto_seal_after', 'int', 'Auto-seal items after (s)', str(5), [1, 120]),
            ],
            'Connection': [
                ('Source.type', 'choice', 'Data source', 'local', [
                    "local:Local file (offline)",
                    "flowkeeper.org:Flowkeeper.org",
                    "flowkeeper.pro:Flowkeeper.pro",
                    "websocket:Self-hosted server",
                ]),
                ('Source.fullname', 'str', 'User full name', 'Local User', []),
                ('Source.username', 'email', 'User email', 'user@local.host', []),
                ('', 'separator', '', '', []),
                ('FileEventSource.filename', 'file', 'Data file', '~/flowkeeper-data.txt', ['*.txt']),
                ('FileEventSource.watch_changes', 'bool', 'Watch changes', 'True', ['*.wav;*.mp3']),
                ('', 'separator', '', '', []),
                ('WebsocketEventSource.url', 'str', 'Server URL', 'wss://app.flowkeeper.org', []),
                ('WebsocketEventSource.password', 'secret', 'Password', '', []),
            ],
            'Appearance': [
                ('Application.timer_ui_mode', 'choice', 'When timer starts', 'focus', [
                    "keep:Keep application window as-is",
                    "focus:Switch to focus mode",
                    "minimize:Hide application window",
                ]),
                ('Application.quit_on_close', 'bool', 'Quit on close', 'False', []),
                ('Application.use_custom_fonts', 'bool', 'Use custom fonts', 'True', []),
                ('Application.show_main_menu', 'bool', 'Show main menu', 'False', []),
                ('Application.show_status_bar', 'bool', 'Show status bar', 'False', []),
                ('Application.show_toolbar', 'bool', 'Show top toolbar', 'False', []),
                ('Application.show_left_toolbar', 'bool', 'Show left toolbar', 'True', []),
                ('Application.show_tray_icon', 'bool', 'Show tray icon', 'True', []),
            ],
            'Audio': [
                ('Application.play_alarm_sound', 'bool', 'Play alarm sound', 'True', []),
                ('Application.alarm_sound_file', 'file', 'Alarm sound file', '../../../res/sound/bell.wav', ['*.wav;*.mp3']),
                ('Application.play_rest_sound', 'bool', 'Play "rest" sound', 'True', []),
                ('Application.rest_sound_file', 'file', '"Rest" sound file', '../../../res/sound/rest.mp3', ['*.wav;*.mp3']),
                ('Application.play_tick_sound', 'bool', 'Play ticking sound', 'True', []),
                ('Application.tick_sound_file', 'file', 'Ticking sound file', '../../../res/sound/tick.wav', ['*.wav;*.mp3']),
            ],
        }

        self._defaults = dict()
        for lst in self._definitions.values():
            for s in lst:
                self._defaults[s[0]] = s[3]
        # print('Filled defaults', self._defaults)

    @abstractmethod
    def set(self, name: str, value: str) -> str:
        pass

    @abstractmethod
    def get(self, name: str) -> str:
        # Note that there's no default value -- we can get it from self._defaults
        pass

    @abstractmethod
    def location(self) -> str:
        pass

    def get_username(self) -> str:
        return self.get('Source.username')

    def get_fullname(self) -> str:
        return self.get('Source.fullname')

    def get_work_duration(self) -> int:
        return int(self.get('Pomodoro.default_work_duration'))

    def get_rest_duration(self) -> int:
        return int(self.get('Pomodoro.default_rest_duration'))

    def get_categories(self) -> Iterable[str]:
        return self._definitions.keys()

    def get_settings(self, category) -> Iterable[tuple[str, str, str, str, list[any]]]:
        return [
            (
                option_id,
                option_type,
                option_display,
                self.get(option_id) if option_type != 'separator' else '',
                option_options
            )
            for option_id, option_type, option_display, option_default, option_options
            in self._definitions[category]
        ]

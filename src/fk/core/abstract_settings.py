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
from pathlib import Path
from typing import Iterable

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter


class AbstractSettings(AbstractEventEmitter, ABC):
    # Category -> [(id, type, display, default, options)]
    _definitions: dict[str, list[tuple[str, str, str, str, list[any], bool]]]
    _defaults: dict[str, str]

    def __init__(self, default_font_family: str, default_font_size: int):
        AbstractEventEmitter.__init__(self, [
            events.BeforeSettingChanged,
            events.AfterSettingChanged,
        ])

        self._definitions = {
            'General': [
                ('Pomodoro.default_work_duration', 'int', 'Default work duration (s)', str(25 * 60), [1, 120 * 60], True),
                ('Pomodoro.default_rest_duration', 'int', 'Default rest duration (s)', str(5 * 60), [1, 60 * 60], True),
                ('Pomodoro.auto_seal_after', 'int', 'Auto-seal items after (s)', str(5), [1, 120], True),
            ],
            'Connection': [
                ('Source.type', 'choice', 'Data source', 'local', [
                    "local:Local file (offline)",
                    "flowkeeper.org:Flowkeeper.org",
                    "flowkeeper.pro:Flowkeeper.pro",
                    "websocket:Self-hosted server",
                ], True),
                ('Source.fullname', 'str', 'User full name', 'Local User', [], True),
                ('Source.username', 'email', 'User email', 'user@local.host', [], True),
                ('', 'separator', '', '', [], True),
                ('FileEventSource.filename', 'file', 'Data file', str(Path.home() / 'flowkeeper-data.txt'), ['*.txt'], True),
                ('FileEventSource.watch_changes', 'bool', 'Watch changes', 'True', ['*.wav;*.mp3'], True),
                ('', 'separator', '', '', [], True),
                ('WebsocketEventSource.url', 'str', 'Server URL', 'wss://app.flowkeeper.org', [], True),
                ('WebsocketEventSource.password', 'secret', 'Password', '', [], True),
            ],
            'Appearance': [
                ('Application.timer_ui_mode', 'choice', 'When timer starts', 'focus', [
                    "keep:Keep application window as-is",
                    "focus:Switch to focus mode",
                    "minimize:Hide application window",
                ], True),
                ('Application.theme', 'choice', 'Theme', 'light', [
                    "auto:Detect automatically",
                    "light:Light",
                    "dark:Dark",
                    "mixed:Mixed",
                    "colorful:Colorful",
                ], True),
                ('Application.quit_on_close', 'bool', 'Quit on close', 'False', [], True),
                ('Application.show_main_menu', 'bool', 'Show main menu', 'False', [], True),
                ('Application.show_status_bar', 'bool', 'Show status bar', 'False', [], True),
                ('Application.show_toolbar', 'bool', 'Show top toolbar', 'False', [], True),
                ('Application.show_left_toolbar', 'bool', 'Show left toolbar', 'True', [], True),
                ('Application.show_tray_icon', 'bool', 'Show tray icon', 'True', [], True),
                ('Application.header_background', 'file', 'Header background', '', ['*.png;*.jpg'], True),
                ('Application.window_width', 'int', 'Main window width', '700', [5, 5000], False),
                ('Application.window_height', 'int', 'Main window height', '500', [5, 5000], False),
                ('Application.window_splitter_width', 'int', 'Splitter width', '200', [0, 5000], False),
            ],
            'Fonts': [
                ('Application.font_main_family', 'font', 'Main font family', default_font_family, [], True),
                ('Application.font_main_size', 'int', 'Main font size', str(default_font_size), [3, 48], True),
                ('Application.font_header_family', 'font', 'Title font family', default_font_family, [], True),
                ('Application.font_header_size', 'int', 'Title font size', str(int(24.0 / 9 * default_font_size)), [3, 72], True),
            ],
            'Audio': [
                ('Application.play_alarm_sound', 'bool', 'Play alarm sound', 'True', [], True),
                ('Application.alarm_sound_file', 'file', 'Alarm sound file', '../../../res/sound/bell.wav', ['*.wav;*.mp3'], True),
                ('Application.play_rest_sound', 'bool', 'Play "rest" sound', 'True', [], True),
                ('Application.rest_sound_file', 'file', '"Rest" sound file', '../../../res/sound/rest.mp3', ['*.wav;*.mp3'], True),
                ('Application.play_tick_sound', 'bool', 'Play ticking sound', 'True', [], True),
                ('Application.tick_sound_file', 'file', 'Ticking sound file', '../../../res/sound/tick.wav', ['*.wav;*.mp3'], True),
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

    def get_settings(self, category) -> Iterable[tuple[str, str, str, str, list[any], bool]]:
        return [
            (
                option_id,
                option_type,
                option_display,
                self.get(option_id) if option_type != 'separator' else '',
                option_options,
                option_visible
            )
            for option_id, option_type, option_display, option_default, option_options, option_visible
            in self._definitions[category]
        ]

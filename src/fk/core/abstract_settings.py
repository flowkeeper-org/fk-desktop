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
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Callable

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.events import get_all_events
from fk.core.sandbox import get_sandbox_type

logger = logging.getLogger(__name__)


def _get_desktop() -> [str]:
    return [s.lower() for s in os.environ.get('XDG_SESSION_DESKTOP', '').split(':')]


def _is_gnome() -> bool:
    return 'gnome' in _get_desktop()


def _always_show(_) -> bool:
    return True


def _never_show(_) -> bool:
    return False


def _show_for_system_font(values: dict[str, str]) -> bool:
    return values['Application.font_embedded'] == 'False'


def _show_for_gradient_eyecandy(values: dict[str, str]) -> bool:
    return values['Application.eyecandy_type'] == 'gradient'


def _show_for_image_eyecandy(values: dict[str, str]) -> bool:
    return values['Application.eyecandy_type'] == 'image'


def _show_for_file_source(values: dict[str, str]) -> bool:
    return values['Source.type'] == 'local'


def _hide_for_ephemeral_source(values: dict[str, str]) -> bool:
    return values['Source.type'] != 'ephemeral'


def _show_for_websocket_source(values: dict[str, str]) -> bool:
    return values['Source.type'] in ('websocket', 'flowkeeper.org', 'flowkeeper.pro')


def _show_when_encryption_is_enabled(values: dict[str, str]) -> bool:
    return values['Source.type'] in ('flowkeeper.org', 'flowkeeper.pro') \
        or values['Source.encryption_enabled'] == 'True'


def _show_when_encryption_is_optional(values: dict[str, str]) -> bool:
    return values['Source.type'] in ('websocket', 'local', 'ephemeral')


def _show_for_custom_websocket_source(values: dict[str, str]) -> bool:
    return values['Source.type'] == 'websocket'


def _show_for_basic_auth(values: dict[str, str]) -> bool:
    return _show_for_websocket_source(values) and values['WebsocketEventSource.auth_type'] == 'basic'


def _show_for_google_auth(values: dict[str, str]) -> bool:
    return _show_for_websocket_source(values) and values['WebsocketEventSource.auth_type'] == 'google'


def _show_if_play_alarm_enabled(values: dict[str, str]) -> bool:
    return values['Application.play_alarm_sound'] == 'True'


def _show_if_signed_in(values: dict[str, str]) -> bool:
    return _show_for_google_auth(values) and values['WebsocketEventSource.username'] != 'user@local.host'


def _show_if_signed_out(values: dict[str, str]) -> bool:
    return _show_for_google_auth(values) and values['WebsocketEventSource.username'] == 'user@local.host'


def _show_if_play_rest_enabled(values: dict[str, str]) -> bool:
    return values['Application.play_rest_sound'] == 'True'


def _show_if_madelene(values: dict[str, str]) -> bool:
    return _show_if_play_rest_enabled(values) and values['Application.rest_sound_file'] == 'qrc:/sound/Madelene.mp3'


def _show_if_play_tick_enabled(values: dict[str, str]) -> bool:
    return values['Application.play_tick_sound'] == 'True'


def _show_for_flatpak(values: dict[str, str]) -> bool:
    return get_sandbox_type() == 'Flatpak'


def _is_tiling_wm() -> bool:
    wm = _get_desktop()
    return ('hyprland' in wm
            or 'i3' in wm
            or 'awesome' in wm)


def prepare_file_for_writing(filename):
    (Path(filename) / '..').resolve().mkdir(parents=True, exist_ok=True)


class AbstractSettings(AbstractEventEmitter, ABC):
    # Category -> [(id, type, display, default, options, visibility)]
    _definitions: dict[str, list[tuple[str, str, str, str, list[any], Callable[[dict[str, str]], bool]]]]
    _defaults: dict[str, str]
    _callback_invoker: Callable

    def __init__(self,
                 default_data_dir: str,
                 default_logs_dir: str,
                 callback_invoker: Callable,
                 is_wayland: bool | None = None):
        AbstractEventEmitter.__init__(self, [
            events.BeforeSettingsChanged,
            events.AfterSettingsChanged,
        ], callback_invoker)

        self._callback_invoker = callback_invoker

        self._defaults = dict()
        self._definitions = {
            'General': [
                ('Pomodoro.default_work_duration', 'duration', 'Default work duration', str(25 * 60), [1, 120 * 60], _always_show),
                ('Pomodoro.default_rest_duration', 'duration', 'Default rest duration', str(5 * 60), [1, 60 * 60], _always_show),
                ('Application.hide_completed', 'bool', 'Hide completed items', 'False', [], _never_show),
                ('', 'separator', '', '', [], _always_show),
                ('Application.feature_tags', 'bool', 'Display #tags', 'True', [], _always_show),
                ('', 'separator', '', '', [], _always_show),
                ('Application.check_updates', 'bool', 'Check for updates', 'True', [], _always_show),
                ('Application.ignored_updates', 'str', 'Ignored updates', '', [], _never_show),
                ('Application.singleton', 'bool', 'Single Flowkeeper instance', 'False', [], _always_show),
                ('Application.hide_on_autostart', 'bool', 'Hide on autostart', 'True', [], _always_show),
                ('', 'separator', '', '', [], _always_show),
                ('Application.shortcuts', 'shortcuts', 'Shortcuts', '{}', [], _always_show),
                ('Application.enable_teams', 'bool', 'Enable teams functionality', 'False', [], _never_show),
                ('Application.show_tutorial', 'bool', 'Show tutorial on start', 'True', [], _never_show),
                ('Application.completed_tutorial_steps', 'str', 'Completed tutrial steps', '', [], _never_show),
                ('', 'separator', '', '', [], _always_show),
                ('Logger.level', 'choice', 'Log level', 'WARNING', [
                    "ERROR:Errors only",
                    "WARNING:Errors and warnings",
                    "DEBUG:Verbose (use it for troubleshooting)",
                ], _always_show),
                ('Logger.filename', 'file', 'Log filename', str(Path(default_logs_dir) / 'flowkeeper.log'), [], _always_show),
                ('Application.ignore_keyring_errors', 'bool', 'Ignore keyring errors', 'False', [], _never_show),
                ('Application.feature_connect', 'bool', 'Enable Connect feature', 'False', [], _never_show),
                ('Application.feature_keyring', 'bool', 'Enable Keyring feature', 'False', [], _never_show),
                ('Application.work_summary_settings', 'str', 'Work Summary UI settings', '{}', [], _never_show),
                ('Application.last_version', 'str', 'Last Flowkeeper version', '0.0.1', [], _never_show),
            ],
            'Connection': [
                ('Source.fullname', 'str', 'User full name', 'Local User', [], _never_show),
                ('Source.type', 'choice', 'Data source', 'local', [
                    "local:Local file (offline)",
                    "flowkeeper.org:Flowkeeper.org (EXPERIMENTAL)",
                    #"flowkeeper.pro:Flowkeeper.pro",
                    "websocket:Self-hosted server (EXPERIMENTAL)",
                    "ephemeral:Ephemeral (in-memory, for testing purposes)",
                ], _always_show),
                ('Source.ignore_errors', 'bool', 'Ignore errors', 'True', [], _always_show),
                ('Source.ignore_invalid_sequence', 'bool', 'Ignore invalid sequences', 'True', [], _always_show),
                ('', 'separator', '', '', [], _hide_for_ephemeral_source),
                ('FileEventSource.filename', 'file', 'Data file', str(Path(default_data_dir) / 'flowkeeper-data.txt'), ['*.txt'], _show_for_file_source),
                ('FileEventSource.watch_changes', 'bool', 'Watch changes', 'False', [], _show_for_file_source),
                ('FileEventSource.repair', 'button', 'Repair', '', [], _show_for_file_source),
                ('FileEventSource.compress', 'button', 'Compress', '', [], _show_for_file_source),
                # UC-2: Setting "Server URL" is only shown for the "Self-hosted server" data source
                ('WebsocketEventSource.url', 'str', 'Server URL', 'ws://localhost:8888/ws', [], _show_for_custom_websocket_source),
                # UC-2: Setting "Authentication" is only shown for the "Self-hosted server" or "Flowkeeper.org" data sources
                ('WebsocketEventSource.auth_type', 'choice', 'Authentication', 'google', [
                    "basic:Simple username and password",
                    "google:Google account (more secure)",
                ], _show_for_websocket_source),
                # UC-2: Setting "User email" is only shown for the "Simple username and password" authentication type
                ('WebsocketEventSource.username', 'email', 'User email', 'user@local.host', [], _show_for_basic_auth),
                ('WebsocketEventSource.consent', 'bool', 'Consent for this username', 'False', [], _never_show),
                # UC-2: Setting "Password" is only shown for the "Simple username and password" authentication type
                ('WebsocketEventSource.password!', 'secret', 'Password', '', [], _show_for_basic_auth),
                ('WebsocketEventSource.refresh_token!', 'secret', 'OAuth Refresh Token', '', [], _never_show),
                # UC-2: Button "Sign in" is only shown if the user is signed out, otherwise "Sign out" is shown
                ('WebsocketEventSource.authenticate', 'button', 'Sign in', '', [], _show_if_signed_out),
                ('WebsocketEventSource.logout', 'button', 'Sign out', '', [], _show_if_signed_in),
                # UC-2: Button "Delete my account" is only shown if the user is signed in
                ('WebsocketEventSource.delete_account', 'button', 'Delete my account', '', ['warning'], _show_if_signed_in),
                ('Source.encryption_separator', 'separator', '', '', [], _always_show),
                # UC-2: Setting "End-to-end encryption" is only shown if the data source is "Local file", "Self-hosted server" or "Ephemeral"
                ('Source.encryption_enabled', 'bool', 'End-to-end encryption', 'False', [], _show_when_encryption_is_optional),
                # UC-2: Setting "End-to-end encryption key" is only shown if "End-to-end encryption" is checked, or if the data source is "Flowkeeper.org"
                ('Source.encryption_key!', 'key', 'End-to-end encryption key', '', [], _show_when_encryption_is_enabled),
                ('Source.encryption_key_cache!', 'secret', 'Encryption key cache', '', [], _never_show),
            ],
            'Appearance': [
                ('Application.timer_ui_mode', 'choice', 'When timer starts', 'keep' if _is_tiling_wm() else 'focus', [
                    "keep:Keep application window as-is",
                    "focus:Switch to focus mode",
                    "minimize:Hide application window",
                ], _always_show),
                ('Application.always_on_top', 'bool', 'Always on top', 'False', [], _always_show),
                ('Application.focus_flavor', 'choice', 'Focus bar flavor', 'minimal', ['classic:Classic (with buttons)',
                                                                                       'minimal:Minimalistic (with context menu)'], _always_show),
                ('Application.tray_icon_flavor', 'choice', 'Tray icon flavor', 'thin-dark', ['thin-light:Thin, light background',
                                                                                                   'thin-dark:Thin, dark background',
                                                                                                   'classic-light:Classic, light background',
                                                                                                   'classic-dark:Classic, dark background'], _always_show),
                ('Application.show_window_title', 'bool', 'Focus window title', str(_is_gnome() or is_wayland), [], _always_show),
                ('Application.theme', 'choice', 'Theme', 'auto', [
                    "auto:Detect automatically (Default)",
                    "light:Light",
                    "dark:Dark",
                    "mixed:Mixed dark & light",
                    "desert:Desert",
                    "beach:Beach volley",
                    "terra:Terra",
                    "motel:Motel",
                    "lime:Sneakers",
                    "resort:Sea resort",
                    "purple:Purple rain",
                    "highlight:Highlight",
                ], _always_show),
                ('Application.quit_on_close', 'bool', 'Quit on close', str(_is_gnome()), [], _always_show),
                ('Application.show_main_menu', 'bool', 'Show main menu', 'False', [], _always_show),
                ('Application.show_status_bar', 'bool', 'Show status bar', 'False', [], _never_show),
                ('Application.show_toolbar', 'bool', 'Show toolbar', 'True', [], _always_show),
                ('Application.show_left_toolbar', 'bool', 'Show left toolbar', 'True', [], _always_show),
                ('Application.show_tray_icon', 'bool', 'Show tray icon', 'True', [], _always_show),
                ('Application.eyecandy_type', 'choice', 'Header background', 'gradient', [
                    "default:Default",
                    "image:Image",
                    "gradient:Gradient",
                ], _always_show),
                # UC-3: Setting "Background image" is only shown if "Header background" = "Image"
                ('Application.eyecandy_image', 'file', 'Background image', '', ['*.png;*.jpg'], _show_for_image_eyecandy),
                # UC-3: Setting "Color scheme" and button "Surprise me!" are only shown if "Header background" = "Gradient"
                ('Application.eyecandy_gradient', 'choice', 'Color scheme', 'NorseBeauty', ['NorseBeauty:NorseBeauty'], _show_for_gradient_eyecandy),
                ('Application.eyecandy_gradient_generate', 'button', 'Surprise me!', '', [], _show_for_gradient_eyecandy),
                ('Application.window_width', 'int', 'Main window width', '700', [5, 5000], _never_show),
                ('Application.window_height', 'int', 'Main window height', '500', [5, 5000], _never_show),
                ('Application.window_splitter_width', 'int', 'Splitter width', '200', [0, 5000], _never_show),
                ('Application.backlogs_visible', 'bool', 'Show backlogs', 'True', [], _never_show),
                ('Application.users_visible', 'bool', 'Show users', 'False', [], _never_show),
                ('Application.last_selected_backlog', 'str', 'Last selected backlog', '', [], _never_show),
                ('Application.table_row_height', 'int', 'Table row height', '30', [0, 5000], _never_show),
                ('Application.show_click_here_hint', 'bool', 'Show "Click here" hint', 'True', [], _never_show),
            ],
            'Fonts': [
                ('Application.font_embedded', 'bool', 'Use embedded font', 'True', [], _always_show),
                ('Application.font_main_family', 'font', 'Main font family', 'Noto Sans', [], _show_for_system_font),
                ('Application.font_main_size', 'int', 'Main font size', '12', [3, 48], _show_for_system_font),
                ('Application.font_header_family', 'font', 'Title font family', 'Noto Sans', [], _show_for_system_font),
                ('Application.font_header_size', 'int', 'Title font size', '30', [3, 72], _show_for_system_font),
            ],
            'Audio': [
                # UC-3: Settings "sound file" and "volume %" are only shown when the corresponding "Play ... sound" settings are checked
                ('Application.play_alarm_sound', 'bool', 'Play alarm sound', 'True', [], _always_show),
                ('Application.alarm_sound_file', 'file', 'Alarm sound file', 'qrc:/sound/bell.wav', ['*.wav;*.mp3'], _show_if_play_alarm_enabled),
                ('Application.alarm_sound_volume', 'int', 'Alarm volume %', '100', [0, 100], _show_if_play_alarm_enabled),
                ('separator', 'separator', '', '', [], _always_show),
                ('Application.play_rest_sound', 'bool', 'Play "rest" sound', 'True', [], _always_show),
                ('Application.rest_sound_file', 'file', '"Rest" sound file', 'qrc:/sound/Madelene.mp3', ['*.wav;*.mp3'], _show_if_play_rest_enabled),
                ('Application.rest_sound_copyright', 'label', 'Copyright', 'Embedded music - "Madelene (ID 1315), (C) Lobo Loco <https://www.musikbrause.de>, CC-BY-NC-ND', [], _show_if_madelene),
                ('Application.rest_sound_volume', 'int', 'Rest volume %', '66', [0, 100], _show_if_play_rest_enabled),
                ('separator', 'separator', '', '', [], _always_show),
                ('Application.play_tick_sound', 'bool', 'Play ticking sound', 'True', [], _always_show),
                ('Application.tick_sound_file', 'file', 'Ticking sound file', 'qrc:/sound/tick.wav', ['*.wav;*.mp3'], _show_if_play_tick_enabled),
                ('Application.tick_sound_volume', 'int', 'Ticking volume %', '50', [0, 100], _show_if_play_tick_enabled),
                ('separator', 'separator', '', '', [], _always_show),
                ('Application.audio_output', 'choice', 'Output device', '#none', ['#none:No audio outputs detected'], _always_show),
            ],
            'Integration': [
                ('Integration.callbacks_label', 'label', '', 'You can run a program for every event in the system. You can use Python f{} syntax for variable substitution:\n'
                                                             '$ espeak "Deleted work item {workitem.get_name()}"\n'
                                                             '$ echo "Received {event}. Available variables: {dir()}"\n'
                                                             'WARNING: Placeholders are substituted as-is, without any sanitization or escaping.', [], _always_show),
                ('Integration.flatpak_spawn', 'bool', 'Prefix commands with flatpak-spawn --host', 'True', [], _show_for_flatpak),
                ('Integration.flatpak_spawn_label', 'label', '', 'IMPORTANT: To run commands on the host (outside of Flatpak sandbox) you have to '
                                                                 'check the above checkbox and then grant Flowkeeper access to dbus. This has a major impact '
                                                                 'on the sandbox security, so do this only when strictly necessary:\n'
                                                                 '$ flatpak override --user --talk-name=org.freedesktop.Flatpak org.flowkeeper.Flowkeeper', [], _show_for_flatpak),
                ('Integration.callbacks', 'keyvalue', '', '{}', get_all_events(), _always_show),
            ],
        }
        for lst in self._definitions.values():
            for s in lst:
                self._defaults[s[0]] = s[3]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Filled defaults', self._defaults)

    def invoke_callback(self, fn: Callable, **kwargs) -> None:
        self._callback_invoker(fn, **kwargs)

    @abstractmethod
    def set(self, values: dict[str, str], force_fire=False) -> None:
        pass

    @abstractmethod
    def get(self, name: str) -> str:
        # Note that there's no default value -- we can get it from self._defaults
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def location(self) -> str:
        pass

    def get_username(self) -> str:
        # UC-3: Username for local and ephemeral sources is "user@local.host". All strategies are executed on behalf of this user. It means that we can't have more than one user locally.
        if self.get('Source.type') == 'local' or self.get('Source.type') == 'ephemeral':
            return 'user@local.host'
        else:
            return self.get('WebsocketEventSource.username')

    def is_team_supported(self) -> bool:
        return self.get('Source.type') != 'local' and self.get('Application.enable_teams') == 'True'

    def is_remote_source(self) -> bool:
        return self.get('Source.type') in ('websocket', 'flowkeeper.org', 'flowkeeper.pro')

    def get_fullname(self) -> str:
        return self.get('Source.fullname')

    def get_work_duration(self) -> float:
        return float(self.get('Pomodoro.default_work_duration'))

    def get_rest_duration(self) -> float:
        return float(self.get('Pomodoro.default_rest_duration'))

    def get_categories(self) -> Iterable[str]:
        return self._definitions.keys()

    def get_settings(self, category) -> Iterable[tuple[str, str, str, str, list[any], Callable[[dict[str, str]], bool]]]:
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

    def _get_property(self, option_id, n) -> str:
        for cat in self._definitions.values():
            for opt in cat:
                if opt[0] == option_id:
                    return opt[n]
        raise Exception(f'Invalid option {option_id}')

    def hide(self, option_id: str) -> None:
        # UC-2: Some of the settings can be hidden in runtime in addition to the "normal" checks
        for cat in self._definitions.values():
            for i, opt in enumerate(cat):
                if opt[0] == option_id:
                    mutable = list(opt)
                    mutable[5] = _never_show
                    cat[i] = tuple(mutable)
                    return
        raise Exception(f'Invalid option {option_id}')

    def get_type(self, option_id) -> str:
        return self._get_property(option_id, 1)

    def get_display_name(self, option_id) -> str:
        return self._get_property(option_id, 2)

    def get_configuration(self, option_id) -> list[any]:
        return self._get_property(option_id, 4)

    def reset_to_defaults(self) -> None:
        to_set = dict[str, str]()
        for lst in self._definitions.values():
            for option_id, option_type, option_display, option_default, option_options, option_visible in lst:
                to_set[option_id] = option_default
        self.clear()
        self.set(to_set)

    def is_e2e_encryption_enabled(self) -> bool:
        return _show_when_encryption_is_enabled({
            'Source.encryption_enabled': self.get('Source.encryption_enabled'),
            'Source.type': self.get('Source.type')
        })

    @abstractmethod
    def is_keyring_enabled(self) -> bool:
        pass

    @abstractmethod
    def get_auto_theme(self) -> str:
        pass

    def get_theme(self) -> str:
        raw = self.get('Application.theme')
        return self.get_auto_theme() if raw == 'auto' else raw

    def update_default(self, name: str, value: str) -> None:
        self._defaults[name] = value

    @abstractmethod
    def init_audio_outputs(self):
        pass

    @abstractmethod
    def init_gradients(self):
        pass

    @abstractmethod
    def init_fonts(self):
        pass

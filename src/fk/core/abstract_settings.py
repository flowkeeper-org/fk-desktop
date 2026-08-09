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
from typing import Iterable, Callable, Final

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.events import get_all_events
from fk.core.sandbox import get_sandbox_type

logger = logging.getLogger(__name__)


class S:
    POMODORO_DEFAULT_WORK_DURATION: Final[str] = 'Pomodoro.default_work_duration'
    POMODORO_DEFAULT_REST_DURATION: Final[str] = 'Pomodoro.default_rest_duration'
    POMODORO_END_OF_WORK_NOTIFICATIONS: Final[str] = 'Pomodoro.end_of_work_notifications'
    POMODORO_END_OF_WORK_NOTIFICATION_DURATION: Final[str] = 'Pomodoro.end_of_work_notification_duration'
    APPLICATION_HIDE_COMPLETED: Final[str] = 'Application.hide_completed'
    APPLICATION_FEATURE_TAGS: Final[str] = 'Application.feature_tags'
    APPLICATION_DEFAULT_WORKITEM_CATEGORY: Final[str] = 'Application.default_workitem_category'
    APPLICATION_DEFAULT_BACKLOG_CATEGORY: Final[str] = 'Application.default_backlog_category'
    APPLICATION_CHECK_UPDATES: Final[str] = 'Application.check_updates'
    APPLICATION_IGNORED_UPDATES: Final[str] = 'Application.ignored_updates'
    APPLICATION_SINGLETON: Final[str] = 'Application.singleton'
    APPLICATION_HIDE_ON_AUTOSTART: Final[str] = 'Application.hide_on_autostart'
    APPLICATION_SHORTCUTS: Final[str] = 'Application.shortcuts'
    APPLICATION_ENABLE_TEAMS: Final[str] = 'Application.enable_teams'
    APPLICATION_SHOW_TUTORIAL: Final[str] = 'Application.show_tutorial'
    APPLICATION_COMPLETED_TUTORIAL_STEPS: Final[str] = 'Application.completed_tutorial_steps'
    LOGGER_LEVEL: Final[str] = 'Logger.level'
    LOGGER_FILENAME: Final[str] = 'Logger.filename'
    APPLICATION_IGNORE_KEYRING_ERRORS: Final[str] = 'Application.ignore_keyring_errors'
    APPLICATION_FEATURE_CONNECT: Final[str] = 'Application.feature_connect'
    APPLICATION_FEATURE_KEYRING: Final[str] = 'Application.feature_keyring'
    APPLICATION_WORK_SUMMARY_SETTINGS: Final[str] = 'Application.work_summary_settings'
    APPLICATION_LAST_VERSION: Final[str] = 'Application.last_version'
    APPLICATION_SELECTED_CATEGORY: Final[str] = 'Application.selected_category'
    POMODORO_LONG_BREAK_ALGORITHM: Final[str] = 'Pomodoro.long_break_algorithm'
    POMODORO_LONG_BREAK_EACH: Final[str] = 'Pomodoro.long_break_each'
    POMODORO_LONG_BREAK_FOCUS: Final[str] = 'Pomodoro.long_break_focus'
    POMODORO_LONG_BREAK_WITHIN: Final[str] = 'Pomodoro.long_break_within'
    POMODORO_START_NEXT_AUTOMATICALLY: Final[str] = 'Pomodoro.start_next_automatically'
    POMODORO_SERIES_EXPLANATION: Final[str] = 'Pomodoro.series_explanation'
    SOURCE_FULLNAME: Final[str] = 'Source.fullname'
    SOURCE_TYPE: Final[str] = 'Source.type'
    SOURCE_IGNORE_ERRORS: Final[str] = 'Source.ignore_errors'
    SOURCE_IGNORE_INVALID_SEQUENCE: Final[str] = 'Source.ignore_invalid_sequence'
    FILEEVENTSOURCE_FILENAME: Final[str] = 'FileEventSource.filename'
    FILEEVENTSOURCE_WATCH_CHANGES: Final[str] = 'FileEventSource.watch_changes'
    FILEEVENTSOURCE_REPAIR: Final[str] = 'FileEventSource.repair'
    FILEEVENTSOURCE_COMPRESS: Final[str] = 'FileEventSource.compress'
    WEBSOCKETEVENTSOURCE_URL: Final[str] = 'WebsocketEventSource.url'
    WEBSOCKETEVENTSOURCE_AUTH_TYPE: Final[str] = 'WebsocketEventSource.auth_type'
    WEBSOCKETEVENTSOURCE_USERNAME: Final[str] = 'WebsocketEventSource.username'
    WEBSOCKETEVENTSOURCE_CONSENT: Final[str] = 'WebsocketEventSource.consent'
    WEBSOCKETEVENTSOURCE_PASSWORD: Final[str] = 'WebsocketEventSource.password!'
    WEBSOCKETEVENTSOURCE_REFRESH_TOKEN: Final[str] = 'WebsocketEventSource.refresh_token!'
    WEBSOCKETEVENTSOURCE_AUTHENTICATE: Final[str] = 'WebsocketEventSource.authenticate'
    WEBSOCKETEVENTSOURCE_LOGOUT: Final[str] = 'WebsocketEventSource.logout'
    WEBSOCKETEVENTSOURCE_DELETE_ACCOUNT: Final[str] = 'WebsocketEventSource.delete_account'
    SOURCE_ENCRYPTION_SEPARATOR: Final[str] = 'Source.encryption_separator'
    SOURCE_ENCRYPTION_ENABLED: Final[str] = 'Source.encryption_enabled'
    SOURCE_ENCRYPTION_KEY: Final[str] = 'Source.encryption_key!'
    SOURCE_ENCRYPTION_KEY_CACHE: Final[str] = 'Source.encryption_key_cache!'
    APPLICATION_TIMER_UI_MODE: Final[str] = 'Application.timer_ui_mode'
    APPLICATION_ALWAYS_ON_TOP: Final[str] = 'Application.always_on_top'
    APPLICATION_FOCUS_FLAVOR: Final[str] = 'Application.focus_flavor'
    APPLICATION_TRAY_ICON_FLAVOR: Final[str] = 'Application.tray_icon_flavor'
    APPLICATION_SHOW_WINDOW_TITLE: Final[str] = 'Application.show_window_title'
    APPLICATION_THEME: Final[str] = 'Application.theme'
    APPLICATION_QUIT_ON_CLOSE: Final[str] = 'Application.quit_on_close'
    APPLICATION_SHOW_MAIN_MENU: Final[str] = 'Application.show_main_menu'
    APPLICATION_SHOW_STATUS_BAR: Final[str] = 'Application.show_status_bar'
    APPLICATION_SHOW_TOOLBAR: Final[str] = 'Application.show_toolbar'
    APPLICATION_SHOW_LEFT_TOOLBAR: Final[str] = 'Application.show_left_toolbar'
    APPLICATION_SHOW_TRAY_ICON: Final[str] = 'Application.show_tray_icon'
    APPLICATION_EYECANDY_TYPE: Final[str] = 'Application.eyecandy_type'
    APPLICATION_EYECANDY_IMAGE: Final[str] = 'Application.eyecandy_image'
    APPLICATION_EYECANDY_GRADIENT: Final[str] = 'Application.eyecandy_gradient'
    APPLICATION_EYECANDY_GRADIENT_GENERATE: Final[str] = 'Application.eyecandy_gradient_generate'
    APPLICATION_WINDOW_WIDTH: Final[str] = 'Application.window_width'
    APPLICATION_WINDOW_HEIGHT: Final[str] = 'Application.window_height'
    APPLICATION_WINDOW_SPLITTER_WIDTH: Final[str] = 'Application.window_splitter_width'
    APPLICATION_BACKLOGS_VISIBLE: Final[str] = 'Application.backlogs_visible'
    APPLICATION_USERS_VISIBLE: Final[str] = 'Application.users_visible'
    APPLICATION_LAST_SELECTED_BACKLOG: Final[str] = 'Application.last_selected_backlog'
    APPLICATION_TABLE_ROW_HEIGHT: Final[str] = 'Application.table_row_height'
    APPLICATION_SHOW_CLICK_HERE_HINT: Final[str] = 'Application.show_click_here_hint'
    APPLICATION_FULL_SCREEN_NOTIFICATIONS: Final[str] = 'Application.full_screen_notifications'
    APPLICATION_FONT_MAIN_FAMILY: Final[str] = 'Application.font_main_family'
    APPLICATION_FONT_MAIN_SIZE: Final[str] = 'Application.font_main_size'
    APPLICATION_FONT_HEADER_FAMILY: Final[str] = 'Application.font_header_family'
    APPLICATION_FONT_HEADER_SIZE: Final[str] = 'Application.font_header_size'
    APPLICATION_PLAY_ALARM_SOUND: Final[str] = 'Application.play_alarm_sound'
    APPLICATION_ALARM_SOUND_FILE: Final[str] = 'Application.alarm_sound_file'
    APPLICATION_ALARM_SOUND_VOLUME: Final[str] = 'Application.alarm_sound_volume'
    SEPARATOR: Final[str] = 'separator'
    APPLICATION_PLAY_REST_SOUND: Final[str] = 'Application.play_rest_sound'
    APPLICATION_REST_SOUND_FILE: Final[str] = 'Application.rest_sound_file'
    APPLICATION_REST_SOUND_COPYRIGHT: Final[str] = 'Application.rest_sound_copyright'
    APPLICATION_REST_SOUND_VOLUME: Final[str] = 'Application.rest_sound_volume'
    APPLICATION_PLAY_TICK_SOUND: Final[str] = 'Application.play_tick_sound'
    APPLICATION_TICK_SOUND_FILE: Final[str] = 'Application.tick_sound_file'
    APPLICATION_TICK_SOUND_VOLUME: Final[str] = 'Application.tick_sound_volume'
    APPLICATION_PLAY_NOTIFICATION_SOUND: Final[str] = 'Application.play_notification_sound'
    APPLICATION_NOTIFICATION_SOUND_FILE: Final[str] = 'Application.notification_sound_file'
    APPLICATION_NOTIFICATION_SOUND_VOLUME: Final[str] = 'Application.notification_sound_volume'
    APPLICATION_AUDIO_OUTPUT: Final[str] = 'Application.audio_output'
    INTEGRATION_CALLBACKS_LABEL: Final[str] = 'Integration.callbacks_label'
    INTEGRATION_FLATPAK_SPAWN: Final[str] = 'Integration.flatpak_spawn'
    INTEGRATION_FLATPAK_SPAWN_LABEL: Final[str] = 'Integration.flatpak_spawn_label'
    INTEGRATION_FLATPAK_COMMAND_LABEL: Final[str] = 'Integration.flatpak_command_label'
    INTEGRATION_CALLBACKS: Final[str] = 'Integration.callbacks'


def _get_desktop() -> [str]:
    return [s.lower() for s in os.environ.get('XDG_SESSION_DESKTOP', '').split(':')]


def _is_gnome() -> bool:
    return 'gnome' in _get_desktop()


def _always_show(_) -> bool:
    return True


def _never_show(_) -> bool:
    return False


def _show_for_simple_long_breaks(values: dict[str, str]) -> bool:
    return values[S.POMODORO_LONG_BREAK_ALGORITHM] == 'simple'


def _show_for_smart_long_breaks(values: dict[str, str]) -> bool:
    return values[S.POMODORO_LONG_BREAK_ALGORITHM] == 'smart'


def _show_for_gradient_eyecandy(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_EYECANDY_TYPE] == 'gradient'


def _show_for_image_eyecandy(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_EYECANDY_TYPE] == 'image'


def _show_for_file_source(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] == 'local'


def _hide_for_ephemeral_source(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] != 'ephemeral'


def _show_for_websocket_source(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] in ('websocket', 'flowkeeper.org', 'flowkeeper.pro')


def _show_when_encryption_is_enabled(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] in ('flowkeeper.org', 'flowkeeper.pro') \
        or values[S.SOURCE_ENCRYPTION_ENABLED] == 'True'


def _show_when_encryption_is_optional(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] in ('websocket', 'local', 'ephemeral')


def _show_for_custom_websocket_source(values: dict[str, str]) -> bool:
    return values[S.SOURCE_TYPE] == 'websocket'


def _show_for_basic_auth(values: dict[str, str]) -> bool:
    return _show_for_websocket_source(values) and values[S.WEBSOCKETEVENTSOURCE_AUTH_TYPE] == 'basic'


def _show_for_google_auth(values: dict[str, str]) -> bool:
    return _show_for_websocket_source(values) and values[S.WEBSOCKETEVENTSOURCE_AUTH_TYPE] == 'google'


def _show_if_play_alarm_enabled(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_PLAY_ALARM_SOUND] == 'True'


def _show_if_end_of_work_notifications_are_enabled(values: dict[str, str]) -> bool:
    return values[S.POMODORO_END_OF_WORK_NOTIFICATIONS] == 'True'


def _show_if_signed_in(values: dict[str, str]) -> bool:
    return _show_for_google_auth(values) and values[S.WEBSOCKETEVENTSOURCE_USERNAME] != 'user@local.host'


def _show_if_signed_out(values: dict[str, str]) -> bool:
    return _show_for_google_auth(values) and values[S.WEBSOCKETEVENTSOURCE_USERNAME] == 'user@local.host'


def _show_if_play_rest_enabled(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_PLAY_REST_SOUND] == 'True'


def _show_if_madelene(values: dict[str, str]) -> bool:
    return _show_if_play_rest_enabled(values) and values[S.APPLICATION_REST_SOUND_FILE] == 'qrc:/sound/Madelene.m4a'


def _show_if_play_tick_enabled(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_PLAY_TICK_SOUND] == 'True'


def _show_if_play_notification_enabled(values: dict[str, str]) -> bool:
    return values[S.APPLICATION_PLAY_NOTIFICATION_SOUND] == 'True'


def _show_for_flatpak(values: dict[str, str]) -> bool:
    return get_sandbox_type() == 'Flatpak'


def _hide_for_sandbox(values: dict[str, str]) -> bool:
    return get_sandbox_type() is None


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
                (S.POMODORO_DEFAULT_WORK_DURATION, 'duration', 'Default work duration', str(25 * 60), [1, 120 * 60], _always_show),
                (S.POMODORO_DEFAULT_REST_DURATION, 'duration', 'Default rest duration', str(5 * 60), [1, 60 * 60], _always_show),
                (S.POMODORO_END_OF_WORK_NOTIFICATIONS, 'bool', 'Notify about end of work', 'True', [], _always_show),
                (S.POMODORO_END_OF_WORK_NOTIFICATION_DURATION, 'duration', 'Notification lead time', str(1 * 60), [1, 120 * 60], _show_if_end_of_work_notifications_are_enabled),
                (S.APPLICATION_HIDE_COMPLETED, 'bool', 'Hide completed items', 'False', [], _never_show),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_FEATURE_TAGS, 'bool', 'Display #tags', 'True', [], _always_show),
                (S.APPLICATION_DEFAULT_WORKITEM_CATEGORY, 'choice', 'For new work items', 'ask', ['ask:Ask for a group', 'none:Create as uncategorized'], _always_show),
                (S.APPLICATION_DEFAULT_BACKLOG_CATEGORY, 'choice', 'For new backlogs', 'last', ['last:Use the last grouping method', 'none:Do not use grouping'], _always_show),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_CHECK_UPDATES, 'bool', 'Check for updates', 'True', [], _hide_for_sandbox),
                (S.APPLICATION_IGNORED_UPDATES, 'str', 'Ignored updates', '', [], _never_show),
                (S.APPLICATION_SINGLETON, 'bool', 'Single Flowkeeper instance', 'False', [], _hide_for_sandbox),
                (S.APPLICATION_HIDE_ON_AUTOSTART, 'bool', 'Hide on autostart', 'True', [], _always_show),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_SHORTCUTS, 'shortcuts', 'Shortcuts', '{}', [], _always_show),
                (S.APPLICATION_ENABLE_TEAMS, 'bool', 'Enable teams functionality', 'False', [], _never_show),
                (S.APPLICATION_SHOW_TUTORIAL, 'bool', 'Show tutorial on start', 'True', [], _never_show),
                (S.APPLICATION_COMPLETED_TUTORIAL_STEPS, 'str', 'Completed tutrial steps', '', [], _never_show),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.LOGGER_LEVEL, 'choice', 'Log level', 'WARNING', [
                    "ERROR:Errors only",
                    "WARNING:Errors and warnings",
                    "DEBUG:Verbose (use it for troubleshooting)",
                ], _always_show),
                (S.LOGGER_FILENAME, 'file', 'Log filename', str(Path(default_logs_dir) / 'flowkeeper.log'), [], _always_show),
                (S.APPLICATION_IGNORE_KEYRING_ERRORS, 'bool', 'Ignore keyring errors', 'False', [], _never_show),
                (S.APPLICATION_FEATURE_CONNECT, 'bool', 'Enable Connect feature', 'False', [], _never_show),
                (S.APPLICATION_FEATURE_KEYRING, 'bool', 'Enable Keyring feature', 'False', [], _never_show),
                (S.APPLICATION_WORK_SUMMARY_SETTINGS, 'str', 'Work Summary UI settings', '{}', [], _never_show),
                (S.APPLICATION_LAST_VERSION, 'str', 'Last Flowkeeper version', '0.0.1', [], _never_show),
                (S.APPLICATION_SELECTED_CATEGORY, 'str', 'Selected workitem group category', '', [], _never_show),
            ],
            'Series and breaks': [
                (S.POMODORO_LONG_BREAK_ALGORITHM, 'choice', 'Take a long break', 'simple', [
                    'simple:After [N] completed pomodoros',
                    # 'smart:After focusing for [X] time within the last [Y] hours',
                    # 'done:After completing a series of pomodoros',
                    'never:Never (let me decide)',
                ], _always_show),
                (S.POMODORO_LONG_BREAK_EACH, 'int', 'N = ', '4', [1, 100], _show_for_simple_long_breaks),
                (S.POMODORO_LONG_BREAK_FOCUS, 'duration', 'X = ', str(3 * 30 * 60), [1, 24 * 60 * 60], _show_for_smart_long_breaks),
                (S.POMODORO_LONG_BREAK_WITHIN, 'duration', 'Y = ', str(4 * 30 * 60), [1, 24 * 60 * 60], _show_for_smart_long_breaks),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.POMODORO_START_NEXT_AUTOMATICALLY, 'bool', 'Work in series', 'False', [], _always_show),
                (S.POMODORO_SERIES_EXPLANATION, 'label', ' ', 'In the series mode Flowkeeper will start the next\n'
                                                              'planned pomodoro in the same work item automatically.', [], _always_show),
                ('', S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_FULL_SCREEN_NOTIFICATIONS, 'bool', 'Full-screen rest notifications', 'True', [],
                 _always_show),
            ],
            'Connection': [
                (S.SOURCE_FULLNAME, 'str', 'User full name', 'Local User', [], _never_show),
                (S.SOURCE_TYPE, 'choice', 'Data source', 'local', [
                    "local:Local file (offline)",
                    "flowkeeper.org:Flowkeeper.org (EXPERIMENTAL)",
                    #"flowkeeper.pro:Flowkeeper.pro",
                    "websocket:Self-hosted server (EXPERIMENTAL)",
                    "ephemeral:Ephemeral (in-memory, for testing purposes)",
                ], _always_show),
                (S.SOURCE_IGNORE_ERRORS, 'bool', 'Ignore errors', 'True', [], _always_show),
                (S.SOURCE_IGNORE_INVALID_SEQUENCE, 'bool', 'Ignore invalid sequences', 'True', [], _always_show),
                ('', S.SEPARATOR, '', '', [], _hide_for_ephemeral_source),
                (S.FILEEVENTSOURCE_FILENAME, 'file', 'Data file', str(Path(default_data_dir) / 'flowkeeper-data.txt'), ['*.txt'], _show_for_file_source),
                (S.FILEEVENTSOURCE_WATCH_CHANGES, 'bool', 'Watch changes', 'False', [], _show_for_file_source),
                (S.FILEEVENTSOURCE_REPAIR, 'button', 'Repair', '', [], _show_for_file_source),
                (S.FILEEVENTSOURCE_COMPRESS, 'button', 'Compress', '', [], _show_for_file_source),
                # UC-2: Setting "Server URL" is only shown for the "Self-hosted server" data source
                (S.WEBSOCKETEVENTSOURCE_URL, 'str', 'Server URL', 'ws://localhost:8888/ws', [], _show_for_custom_websocket_source),
                # UC-2: Setting "Authentication" is only shown for the "Self-hosted server" or "Flowkeeper.org" data sources
                (S.WEBSOCKETEVENTSOURCE_AUTH_TYPE, 'choice', 'Authentication', 'google', [
                    "basic:Simple username and password",
                    "google:Google account (more secure)",
                ], _show_for_websocket_source),
                # UC-2: Setting "User email" is only shown for the "Simple username and password" authentication type
                (S.WEBSOCKETEVENTSOURCE_USERNAME, 'email', 'User email', 'user@local.host', [], _show_for_basic_auth),
                (S.WEBSOCKETEVENTSOURCE_CONSENT, 'bool', 'Consent for this username', 'False', [], _never_show),
                # UC-2: Setting "Password" is only shown for the "Simple username and password" authentication type
                (S.WEBSOCKETEVENTSOURCE_PASSWORD, 'secret', 'Password', '', [], _show_for_basic_auth),
                (S.WEBSOCKETEVENTSOURCE_REFRESH_TOKEN, 'secret', 'OAuth Refresh Token', '', [], _never_show),
                # UC-2: Button "Sign in" is only shown if the user is signed out, otherwise "Sign out" is shown
                (S.WEBSOCKETEVENTSOURCE_AUTHENTICATE, 'button', 'Sign in', '', [], _show_if_signed_out),
                (S.WEBSOCKETEVENTSOURCE_LOGOUT, 'button', 'Sign out', '', [], _show_if_signed_in),
                # UC-2: Button "Delete my account" is only shown if the user is signed in
                (S.WEBSOCKETEVENTSOURCE_DELETE_ACCOUNT, 'button', 'Delete my account', '', ['warning'], _show_if_signed_in),
                (S.SOURCE_ENCRYPTION_SEPARATOR, S.SEPARATOR, '', '', [], _always_show),
                # UC-2: Setting "End-to-end encryption" is only shown if the data source is "Local file", "Self-hosted server" or "Ephemeral"
                (S.SOURCE_ENCRYPTION_ENABLED, 'bool', 'End-to-end encryption', 'False', [], _show_when_encryption_is_optional),
                # UC-2: Setting "End-to-end encryption key" is only shown if "End-to-end encryption" is checked, or if the data source is "Flowkeeper.org"
                (S.SOURCE_ENCRYPTION_KEY, 'key', 'End-to-end encryption key', '', [], _show_when_encryption_is_enabled),
                (S.SOURCE_ENCRYPTION_KEY_CACHE, 'secret', 'Encryption key cache', '', [], _never_show),
            ],
            'Appearance': [
                (S.APPLICATION_TIMER_UI_MODE, 'choice', 'When timer starts', 'keep' if _is_tiling_wm() else 'focus', [
                    "keep:Keep application window as-is",
                    "focus:Switch to focus mode",
                    "minimize:Hide application window",
                ], _always_show),
                (S.APPLICATION_ALWAYS_ON_TOP, 'bool', 'Always on top', 'False', [], _never_show if is_wayland else _always_show),
                (S.APPLICATION_FOCUS_FLAVOR, 'choice', 'Focus bar flavor', 'minimal', ['classic:Classic (with buttons)',
                                                                                       'minimal:Minimalistic (with context menu)'], _always_show),
                (S.APPLICATION_TRAY_ICON_FLAVOR, 'choice', 'Tray icon flavor', 'classic-dark', ['thin-light:Thin, light background',
                                                                                                'thin-dark:Thin, dark background',
                                                                                                'classic-light:Classic, light background',
                                                                                                'classic-dark:Classic, dark background'], _always_show),
                (S.APPLICATION_SHOW_WINDOW_TITLE, 'bool', 'Focus window title', str(_is_gnome() or is_wayland), [], _never_show if is_wayland else _always_show),
                (S.APPLICATION_THEME, 'choice', 'Theme', 'auto', [
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
                (S.APPLICATION_QUIT_ON_CLOSE, 'bool', 'Quit on close', str(_is_gnome()), [], _always_show),
                (S.APPLICATION_SHOW_MAIN_MENU, 'bool', 'Show main menu', 'False', [], _always_show),
                (S.APPLICATION_SHOW_STATUS_BAR, 'bool', 'Show status bar', 'False', [], _never_show),
                (S.APPLICATION_SHOW_TOOLBAR, 'bool', 'Show toolbar', 'True', [], _always_show),
                (S.APPLICATION_SHOW_LEFT_TOOLBAR, 'bool', 'Show left toolbar', 'True', [], _always_show),
                (S.APPLICATION_SHOW_TRAY_ICON, 'bool', 'Show tray icon', 'True', [], _always_show),
                (S.APPLICATION_EYECANDY_TYPE, 'choice', 'Header background', 'gradient', [
                    "default:Default",
                    "image:Image",
                    "gradient:Gradient",
                ], _always_show),
                # UC-3: Setting "Background image" is only shown if "Header background" = "Image"
                (S.APPLICATION_EYECANDY_IMAGE, 'file', 'Background image', ':/img/bg.svg', ['*.png;*.jpg;*.svg'], _show_for_image_eyecandy),
                # UC-3: Setting "Color scheme" and button "Surprise me!" are only shown if "Header background" = "Gradient"
                (S.APPLICATION_EYECANDY_GRADIENT, 'choice', 'Color scheme', 'StarWine', ['StarWine:StarWine'], _show_for_gradient_eyecandy),
                (S.APPLICATION_EYECANDY_GRADIENT_GENERATE, 'button', 'Surprise me!', '', [], _show_for_gradient_eyecandy),
                (S.APPLICATION_WINDOW_WIDTH, 'int', 'Main window width', '700', [5, 5000], _never_show),
                (S.APPLICATION_WINDOW_HEIGHT, 'int', 'Main window height', '500', [5, 5000], _never_show),
                (S.APPLICATION_WINDOW_SPLITTER_WIDTH, 'int', 'Splitter width', '200', [0, 5000], _never_show),
                (S.APPLICATION_BACKLOGS_VISIBLE, 'bool', 'Show backlogs', 'True', [], _never_show),
                (S.APPLICATION_USERS_VISIBLE, 'bool', 'Show users', 'False', [], _never_show),
                (S.APPLICATION_LAST_SELECTED_BACKLOG, 'str', 'Last selected backlog', '', [], _never_show),
                (S.APPLICATION_TABLE_ROW_HEIGHT, 'int', 'Table row height', '30', [0, 5000], _never_show),
                (S.APPLICATION_SHOW_CLICK_HERE_HINT, 'bool', 'Show "Click here" hint', 'True', [], _never_show),
            ],
            'Fonts': [
                (S.APPLICATION_FONT_MAIN_FAMILY, 'font', 'Main font family', 'Noto Sans', [], _always_show),
                (S.APPLICATION_FONT_MAIN_SIZE, 'int', 'Main font size', '10', [3, 48], _always_show),
                (S.APPLICATION_FONT_HEADER_FAMILY, 'font', 'Title font family', 'Noto Sans', [], _always_show),
                (S.APPLICATION_FONT_HEADER_SIZE, 'int', 'Title font size', '24', [3, 72], _always_show),
            ],
            'Audio': [
                # UC-3: Settings "sound file" and "volume %" are only shown when the corresponding "Play ... sound" settings are checked
                (S.APPLICATION_PLAY_ALARM_SOUND, 'bool', 'Play alarm sound', 'True', [], _always_show),
                (S.APPLICATION_ALARM_SOUND_FILE, 'file', 'Alarm sound file', 'qrc:/sound/bell.m4a', ['*.wav;*.mp3;*.m4a'], _show_if_play_alarm_enabled),
                (S.APPLICATION_ALARM_SOUND_VOLUME, 'int', 'Alarm volume %', '100', [0, 100], _show_if_play_alarm_enabled),
                (S.SEPARATOR, S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_PLAY_REST_SOUND, 'bool', 'Play "rest" sound', 'True', [], _always_show),
                (S.APPLICATION_REST_SOUND_FILE, 'file', '"Rest" sound file', 'qrc:/sound/Madelene.m4a', ['*.wav;*.mp3;*.m4a'], _show_if_play_rest_enabled),
                (S.APPLICATION_REST_SOUND_COPYRIGHT, 'label', 'Copyright', 'Embedded music - "Madelene (ID 1315)", (C) Lobo Loco\n<https://www.musikbrause.de>, CC-BY-NC-ND', [], _show_if_madelene),
                (S.APPLICATION_REST_SOUND_VOLUME, 'int', 'Rest volume %', '66', [0, 100], _show_if_play_rest_enabled),
                (S.SEPARATOR, S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_PLAY_TICK_SOUND, 'bool', 'Play ticking sound', 'True', [], _always_show),
                (S.APPLICATION_TICK_SOUND_FILE, 'file', 'Ticking sound file', 'qrc:/sound/tick.m4a', ['*.wav;*.mp3;*.m4a'], _show_if_play_tick_enabled),
                (S.APPLICATION_TICK_SOUND_VOLUME, 'int', 'Ticking volume %', '50', [0, 100], _show_if_play_tick_enabled),
                (S.SEPARATOR, S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_PLAY_NOTIFICATION_SOUND, 'bool', 'Play notification sound', 'True', [], _always_show),
                (S.APPLICATION_NOTIFICATION_SOUND_FILE, 'file', 'Notification sound file', 'qrc:/sound/knock.m4a', ['*.wav;*.mp3;*.m4a'], _show_if_play_notification_enabled),
                (S.APPLICATION_NOTIFICATION_SOUND_VOLUME, 'int', 'Notification volume %', '100', [0, 100], _show_if_play_notification_enabled),
                (S.SEPARATOR, S.SEPARATOR, '', '', [], _always_show),
                (S.APPLICATION_AUDIO_OUTPUT, 'choice', 'Output device', '#none', ['#none:No audio outputs detected'], _always_show),
            ],
            'Integration': [
                (S.INTEGRATION_CALLBACKS_LABEL, 'label', '', 'You can run a program for every event in the system. You can use Python f{}\n'
                                                             'syntax for variable substitution:\n'
                                                             '$ espeak "Deleted work item {workitem.get_name()}"\n'
                                                             '$ echo "Received {event}. Available variables: {dir()}"\n'
                                                             'WARNING: Placeholders are substituted as-is, without any sanitization.', [], _always_show),
                (S.INTEGRATION_FLATPAK_SPAWN, 'bool', 'Prefix commands with flatpak-spawn --host', 'True', [], _show_for_flatpak),
                (S.INTEGRATION_FLATPAK_SPAWN_LABEL, 'label', '', 'IMPORTANT: To run commands on the host (outside of Flatpak sandbox) you have to check\n'
                                                                 'the above checkbox and then grant Flowkeeper access to dbus. This has a major impact\n'
                                                                 'on the sandbox security, so do this only when strictly necessary.', [], _show_for_flatpak),
                (S.INTEGRATION_FLATPAK_COMMAND_LABEL, 'label', '', '$ flatpak override --user --talk-name=org.freedesktop.Flatpak org.flowkeeper.Flowkeeper', ['copyable'], _show_for_flatpak),
                (S.INTEGRATION_CALLBACKS, 'keyvalue', '', '{}', get_all_events(), _always_show),
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
    def is_set(self, name: str) -> bool:
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
        if self.get(S.SOURCE_TYPE) == 'local' or self.get(S.SOURCE_TYPE) == 'ephemeral':
            return 'user@local.host'
        else:
            return self.get(S.WEBSOCKETEVENTSOURCE_USERNAME)

    def is_team_supported(self) -> bool:
        return self.get(S.SOURCE_TYPE) != 'local' and self.get(S.APPLICATION_ENABLE_TEAMS) == 'True'

    def is_remote_source(self) -> bool:
        return self.get(S.SOURCE_TYPE) in ('websocket', 'flowkeeper.org', 'flowkeeper.pro')

    def get_fullname(self) -> str:
        return self.get(S.SOURCE_FULLNAME)

    def get_work_duration(self) -> float:
        return float(self.get(S.POMODORO_DEFAULT_WORK_DURATION))

    def get_rest_duration(self) -> float:
        return float(self.get(S.POMODORO_DEFAULT_REST_DURATION))

    def get_categories(self) -> Iterable[str]:
        return self._definitions.keys()

    def get_settings(self, category) -> Iterable[tuple[str, str, str, str, list[any], Callable[[dict[str, str]], bool]]]:
        return [
            (
                option_id,
                option_type,
                option_display,
                self.get(option_id) if option_type != S.SEPARATOR else '',
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
        # It seems to be sufficient just to clear all settings -- then defaults will be
        # used when we do .get(name)
        # to_set = dict[str, str]()
        # for lst in self._definitions.values():
        #     for option_id, option_type, option_display, option_default, option_options, option_visible in lst:
        #         to_set[option_id] = option_default
        self.clear()
        # self.set(to_set)

    def is_e2e_encryption_enabled(self) -> bool:
        return _show_when_encryption_is_enabled({
            S.SOURCE_ENCRYPTION_ENABLED: self.get(S.SOURCE_ENCRYPTION_ENABLED),
            S.SOURCE_TYPE: self.get(S.SOURCE_TYPE)
        })

    @abstractmethod
    def is_keyring_enabled(self) -> bool:
        pass

    @abstractmethod
    def get_auto_theme(self) -> str:
        pass

    def get_theme(self) -> str:
        raw = self.get(S.APPLICATION_THEME)
        return self.get_auto_theme() if raw == 'auto' else raw

    def update_default(self, name: str, value: str) -> None:
        old = self._defaults[name]
        self._defaults[name] = value
        logger.debug(f'Updated default {name} from {old} to {value}. Got: {self.get(name)}')

    @abstractmethod
    def init_audio_outputs(self):
        pass

    @abstractmethod
    def init_gradients(self):
        pass

    @abstractmethod
    def init_fonts(self):
        pass

    @abstractmethod
    def init_appearance(self):
        pass

    @abstractmethod
    def init_network_access(self):
        pass

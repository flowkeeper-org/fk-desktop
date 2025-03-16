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
import datetime
import json
import logging
import platform
import secrets
import sys
import traceback
import urllib
import webbrowser
from pathlib import Path
from typing import Callable

from PySide6 import QtCore
from PySide6.QtCore import QFile, Signal, QStandardPaths
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QGradient, QIcon, QColor
from PySide6.QtGui import QFontDatabase
from PySide6.QtNetwork import QNetworkProxyFactory
from PySide6.QtNetwork import QTcpServer, QHostAddress
from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog, QCheckBox
from semantic_version import Version

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings, prepare_file_for_writing
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.event_source_factory import EventSourceFactory
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterSettingsChanged, BeforeSettingsChanged
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.file_event_source import FileEventSource
from fk.core.integration_executor import IntegrationExecutor
from fk.core.no_cryptograph import NoCryptograph
from fk.core.sandbox import get_sandbox_type
from fk.core.tenant import Tenant
from fk.desktop.desktop_strategies import DeleteAccountStrategy
from fk.desktop.export_wizard import ExportWizard
from fk.desktop.import_wizard import ImportWizard
from fk.desktop.settings import SettingsDialog
from fk.desktop.stats_window import StatsWindow
from fk.desktop.work_summary_window import WorkSummaryWindow
from fk.qt.about_window import AboutWindow
from fk.qt.actions import Actions
from fk.qt.app_version import get_latest_version, get_current_version
from fk.qt.heartbeat import Heartbeat
from fk.qt.oauth import authenticate, AuthenticationRecord, open_url
from fk.qt.qt_filesystem_watcher import QtFilesystemWatcher
from fk.qt.qt_invoker import invoke_in_main_thread
from fk.qt.qt_settings import QtSettings
from fk.qt.qt_timer import QtTimer
from fk.qt.threaded_event_source import ThreadedEventSource
from fk.qt.websocket_event_source import WebsocketEventSource

logger = logging.getLogger(__name__)

AfterFontsChanged = "AfterFontsChanged"
NewReleaseAvailable = "NewReleaseAvailable"


def setting_requires_new_source(name: str) -> bool:
    return name == 'Source.type' or \
        name.startswith('WebsocketEventSource.') or \
        name.startswith('FileEventSource.') or \
        name == 'Source.ignore_errors' or \
        name == 'Source.ignore_invalid_sequence' or \
        name == 'Source.encryption_enabled' or \
        name == 'Source.encryption_key!'

class Application(QApplication, AbstractEventEmitter):
    _settings: AbstractSettings
    _cryptograph: AbstractCryptograph
    _font_main: QFont
    _font_header: QFont
    _embedded_font_family: str | None
    _row_height: int
    _source_holder: EventSourceHolder | None
    _heartbeat: Heartbeat | None
    _version_timer: QtTimer
    _integration_executor: IntegrationExecutor
    _current_version: Version

    upgraded = Signal(Version)

    def __init__(self, args: [str]):
        super().__init__(args,
                         allowed_events=[AfterFontsChanged, NewReleaseAvailable],
                         callback_invoker=invoke_in_main_thread)
        # It's important to import Common theme very early, because we need it to get app version, etc.
        # noinspection PyUnresolvedReferences
        import fk.desktop.resources
        self._current_version = get_current_version()

        self.setDesktopFileName('org.flowkeeper.Flowkeeper')    # This makes KDE on Wayland use the correct icon
        self.setApplicationName('flowkeeper')
        self.setApplicationDisplayName('Flowkeeper')
        self.setApplicationVersion(str(self._current_version))

        if '--version' in self.arguments():
            # This might be useful on Windows or macOS, which store their settings in some obscure locations
            print(f'Flowkeeper v{self._current_version}')
            sys.exit(0)

        self._register_source_producers()
        self._heartbeat = None
        self._embedded_font_family = None
        QNetworkProxyFactory.setUseSystemConfiguration(True)

        # It's important to initialize settings after the QApplication
        # has been constructed, as it uses default QFont and other
        # OS-specific values
        if self.is_e2e_mode():
            self._settings = QtSettings('flowkeeper-desktop-e2e')
            self._settings.reset_to_defaults()
            self._initialize_logger()
            if self._settings.is_keyring_enabled():
                self._cryptograph = FernetCryptograph(self._settings)
            else:
                self._cryptograph = NoCryptograph(self._settings)
            if self.is_screenshot_mode():
                from fk.e2e.screenshots_e2e import ScreenshotE2eTest
                test = ScreenshotE2eTest(self)
            else:
                from fk.e2e.backlog_e2e import BacklogE2eTest
                test = BacklogE2eTest(self)
            sys.excepthook = test.on_exception
            test.start()
        else:
            sys.excepthook = self.on_exception
            if self.is_testing_mode():
                self._settings = QtSettings('flowkeeper-desktop-testing')
                self._settings.reset_to_defaults()
                self._settings.set({
                    'FileEventSource.filename': str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)) / 'flowkeeper-testing.txt'),
                    'Application.show_tutorial': 'False',
                    'Application.check_updates': 'False',
                    'Pomodoro.default_work_duration': '5',
                    'Pomodoro.default_rest_duration': '5',
                    'Application.play_alarm_sound': 'False',
                    'Application.play_rest_sound': 'False',
                    'Application.play_tick_sound': 'False',
                    'Logger.filename': str(Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)) / 'flowkeeper-testing.log'),
                    'Logger.level': 'DEBUG',
                    'Source.encryption_key!': 'test key',
                })
            else:
                self._settings = QtSettings()
                if self._settings.get('Application.singleton') == 'True' and self.is_another_instance_running():
                    logger.warning(f'Another instance of Flowkeeper is running - exiting')
                    sys.exit(3)
            self._initialize_logger()
            if self._settings.is_keyring_enabled():
                self._cryptograph = FernetCryptograph(self._settings)
            else:
                self._cryptograph = NoCryptograph(self._settings)
        self._settings.on(BeforeSettingsChanged, self._before_settings_changed)
        self._settings.on(AfterSettingsChanged, self._after_settings_changed)

        # Quit app on close
        quit_on_close = (self._settings.get('Application.quit_on_close') == 'True')
        self.setQuitOnLastWindowClosed(quit_on_close)

        # Fonts, styles, etc.
        self.refresh_theme_and_fonts()
        self._row_height = self._auto_resize()

        # Version checks
        self._version_timer = QtTimer('Version checker')
        self.on(NewReleaseAvailable, self.on_new_version)
        if self._settings.get('Application.check_updates') == 'True':
            self._version_timer.schedule(5000, self.check_version, None, True)

        QtTimer('Upgrade checker').schedule(1000, self._check_upgrade, None, True)

        self._source_holder = EventSourceHolder(self._settings, self._cryptograph)
        self._source_holder.on(AfterSourceChanged, self._on_source_changed, True)

        # Heartbeat
        self._heartbeat = Heartbeat(self._source_holder, 3000, 500)
        self._heartbeat.on(events.WentOffline, self._on_went_offline)
        self._heartbeat.on(events.WentOnline, self._on_went_online)

        self._integration_executor = IntegrationExecutor(self._settings)

    def _get_versions(self):
        return (f'- Flowkeeper: {self._current_version}\n'
                f'- Qt: {QtCore.__version__} ({self.platformName()})\n'
                f'- Python: {sys.version}\n'
                f'- Platform: {platform.system()} {platform.release()} {platform.version()}\n'
                f'- Sandbox: {get_sandbox_type()}\n'
                f'- Kernel: {platform.platform()}\n')

    def _initialize_logger(self):
        debug = '--debug' in self.arguments()

        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        root = logging.getLogger()

        # 0. Set the overall log level that would apply to ALL handlers
        root.setLevel(logging.DEBUG if debug else self._settings.get('Logger.level'))

        # 1. Remove existing handlers, if any
        for existing_handle in root.handlers:
            existing_handle.close()
        root.handlers.clear()

        # 2. Check that the entire logger file path exists
        filename = self._settings.get('Logger.filename')
        logfile = Path(filename)
        if logfile.is_dir():    # Fixing #108 - a rare case when the user selects directory as log filename
            logfile /= 'flowkeeper.log'
            filename = logfile.absolute()
        prepare_file_for_writing(filename)

        # 3. Add FILE handler for whatever the user configured
        file_handler = logging.FileHandler(filename=filename)
        file_handler.setFormatter(log_format)
        file_handler.setLevel(logging.DEBUG if debug else self._settings.get('Logger.level'))
        root.handlers.append(file_handler)

        # 4. Add STDIO handler for warnings and errors
        stdio_handler = logging.StreamHandler(sys.stdout)
        stdio_handler.setFormatter(log_format)
        stdio_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
        root.handlers.append(stdio_handler)

        logger.debug(f'Versions: \n{self._get_versions()}')

    def _check_upgrade(self, event: str, when: datetime.datetime | None = None):
        from_version = Version(self._settings.get('Application.last_version'))
        if self._current_version != from_version:
            to_set = {'Application.last_version': str(self._current_version)}
            logger.info(f'We execute for the first time after upgrade from {from_version} to {self._current_version}')
            if from_version.major == 0 and 10 > from_version.minor > 0:
                logger.debug(f'Upgrading from 0.9.1 or older, checking data filename')
                if not self._settings.is_set('FileEventSource.filename'):
                    old_filename = Path.home() / 'flowkeeper-data.txt'
                    if old_filename.exists():
                        logger.debug(f'Default filename is used and the file exists -- will keep using it')
                        to_set['FileEventSource.filename'] = str(old_filename.absolute())
            self.upgraded.emit(from_version)
            self._settings.set(to_set)

    def initialize_source(self):
        self._source_holder.request_new_source()

    def _register_source_producers(self):
        def local_source_producer(settings: AbstractSettings, cryptograph: AbstractCryptograph, root: Tenant):
            inner_source = FileEventSource[Tenant](settings, cryptograph, root, QtFilesystemWatcher())
            return ThreadedEventSource(inner_source, self)

        EventSourceFactory.get_event_source_factory().register_producer('local', local_source_producer)

        def ephemeral_source_producer(settings: AbstractSettings, cryptograph: AbstractCryptograph, root: Tenant):
            inner_source = EphemeralEventSource[Tenant](settings, cryptograph, root)
            return ThreadedEventSource(inner_source, self)

        EventSourceFactory.get_event_source_factory().register_producer('ephemeral', ephemeral_source_producer)

        def websocket_source_producer(settings: AbstractSettings, cryptograph: AbstractCryptograph, root: Tenant):
            return WebsocketEventSource[Tenant](settings, cryptograph, self, root)

        EventSourceFactory.get_event_source_factory().register_producer('websocket', websocket_source_producer)
        EventSourceFactory.get_event_source_factory().register_producer('flowkeeper.org', websocket_source_producer)
        EventSourceFactory.get_event_source_factory().register_producer('flowkeeper.pro', websocket_source_producer)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        try:
            logger.debug(f'Application: Received AfterSourceChanged for {source}')
            logger.debug(f'Application: Starting the event source')
            source.start()
            logger.debug(f'Application: Event source started successfully')
        except Exception as e:
            logger.error(f'Application: Error on source change', exc_info=e)
            raise e

    def is_e2e_mode(self):
        return '--e2e' in self.arguments()

    def is_hide_on_start(self):
        return ('--autostart' in self.arguments() and
                self.get_settings().get('Application.hide_on_autostart') == 'True' and
                self.get_settings().get('Application.show_tray_icon') == 'True')

    def is_screenshot_mode(self):
        return '--screenshots' in self.arguments()

    def is_testing_mode(self):
        return '--testing' in self.arguments()

    def _on_went_offline(self, event, after: int, last_received: datetime.datetime) -> None:
        # TODO -- lock the UI
        logger.warning(f'WARNING - We detected that the client went offline after {after}ms. Last '
                       f'time we heard from the server was {last_received}')

    def _on_went_online(self, event, ping: int) -> None:
        # TODO -- unlock the UI
        logger.info(f'We are (back) online with the roundtrip delay of {ping}ms')

    def get_settings(self):
        return self._settings

    def get_source_holder(self):
        return self._source_holder

    def get_theme_variables(self) -> dict[str, str]:
        theme = self._settings.get_theme()
        var_file = QFile(f":/style-{theme}.json")
        var_file.open(QFile.OpenModeFlag.ReadOnly)
        variables = json.loads(var_file.readAll().toStdString())
        var_file.close()
        variables['FONT_HEADER_FAMILY'] = self._settings.get('Application.font_header_family')
        variables['FONT_MAIN_FAMILY'] = self._settings.get('Application.font_main_family')
        variables['FONT_HEADER_SIZE'] = self._settings.get('Application.font_header_size') + 'pt'
        variables['FONT_MAIN_SIZE'] = self._settings.get('Application.font_main_size') + 'pt'
        variables['FONT_SUBTEXT_SIZE'] = str(float(self._settings.get('Application.font_main_size')) * 0.75) + 'pt'
        return variables

    def get_icon_theme(self):
        return self.get_theme_variables()['ICON_THEME']

    # noinspection PyUnresolvedReferences
    def refresh_theme_and_fonts(self):
        logger.debug('Refreshing theme and fonts')

        self._load_embedded_font()

        template_file = QFile(":/style-template.qss")
        template_file.open(QFile.OpenModeFlag.ReadOnly)
        qss = template_file.readAll().toStdString()
        template_file.close()

        variables = self.get_theme_variables()

        for name in variables:
            value = variables[name]
            qss = qss.replace(f'${name}', value)

        QIcon.setThemeName(variables['ICON_THEME'])

        self.setStyleSheet(qss)
        logger.debug('Stylesheet loaded')

        # In Qt 6.7.x it is important to do this AFTER we load the stylesheet, otherwise the fonts
        # are not loaded correctly at startup
        self._initialize_fonts()

    def _load_embedded_font(self):
        # First import embedded font into Qt fonts database
        embedded_font_id = QFontDatabase.addApplicationFont(":/NotoSans.ttf")
        families = QFontDatabase.applicationFontFamilies(embedded_font_id)
        if len(families) > 0:
            self._embedded_font_family = families[0]

    def _initialize_fonts(self) -> (QFont, QFont):
        default_header_size = int(self._settings.get('Application.font_header_size'))
        logger.debug(f'Header font: {self._settings.get("Application.font_header_family")}, size {default_header_size}')
        self._font_header = QFont(self._settings.get('Application.font_header_family'), default_header_size)
        if self._font_header is None:
            self._font_header = QFont()
            new_size = int(self._font_header.pointSize() * 24.0 / 9)
            self._font_header.setPointSize(new_size)

        default_main_size = int(self._settings.get('Application.font_main_size'))
        logger.debug(f'Main font: {self._settings.get("Application.font_main_family")}, size {default_main_size}')
        self._font_main = QFont(self._settings.get('Application.font_main_family'), default_main_size)
        if self._font_main is None:
            self._font_main = QFont()

        self.setFont(self._font_main)

        logger.debug(f'Initialized main font: {self._font_main.family()} / {self._font_main.pointSize()}')
        logger.debug(f'Initialized header font: {self._font_header.family()} / {self._font_header.pointSize()}')

        # Notify everyone
        self._emit(AfterFontsChanged, {
            'main_font': self._font_main,
            'header_font': self._font_header,
            'application': self
        })

        self._auto_resize()

    def _auto_resize(self) -> int:
        h: int = QFontMetrics(self._font_main).height() + 8
        # users_table.verticalHeader().setDefaultSectionSize(h)
        # backlogs_table.verticalHeader().setDefaultSectionSize(h)
        # workitems_table.verticalHeader().setDefaultSectionSize(h)
        # Save it to Settings, so that we can use this value when
        # calculating display hints for the Pomodoro Delegate.
        # As of now, this requires app restart to apply.
        self._settings.set({'Application.table_row_height': str(h)})
        return h

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        logger.error(f"Global exception handler. Full log: {to_log}")
        if (QMessageBox().critical(self.activeWindow(),
                                   "Unexpected error",
                                   f"{exc_type.__name__}: {exc_value}\nWe will appreciate it if you click Open to report it on GitHub.",
                                   QMessageBox.StandardButton.Ok,
                                   QMessageBox.StandardButton.Open)
                == QMessageBox.StandardButton.Open):
            versions = self._get_versions().replace('#', '# ')
            params = urllib.parse.urlencode({
                'labels': 'exception',
                'title': f'Unhandled {exc_type.__name__}',
                'body': f'**Please explain here what you were doing**\n\n'
                        f'Versions:\n'
                        f'{versions}\n'
                        f'Stack trace:\n'
                        f'```\n{to_log}```'
            })
            webbrowser.open(f"https://github.com/flowkeeper-org/fk-desktop/issues/new?{params}")

    def bad_file_for_file_source(self):
        filename = self.get_settings().get('FileEventSource.filename')
        if (QMessageBox().critical(self.activeWindow(),
                                   "Bad data file",
                                   f"The data file you chose ({filename}) is a directory. Please select a valid file.",
                                   QMessageBox.StandardButton.Open)
                == QMessageBox.StandardButton.Open):
            SettingsDialog.do_browse_simple(filename,
                                            lambda v: self.get_settings().set({'FileEventSource.filename': v}))

    def get_main_font(self):
        return self._font_main

    def get_header_font(self):
        return self._font_header

    def get_row_height(self):
        return self._row_height

    def _before_settings_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        for name in new_values.keys():
            if setting_requires_new_source(name):
                # UC-1: Before a new event source is created, the old one unsubscribes all listeners and disconnects
                logger.debug(f'Close old event source before settings change')
                self._source_holder.close_current_source()
                return

    def _after_settings_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        logger.debug(f'Settings changed from {old_values} to {new_values}')

        request_ui_refresh = False
        request_new_source = False
        request_logger_change = False

        for name in new_values.keys():
            if setting_requires_new_source(name):
                request_new_source = True
            elif name == 'Application.quit_on_close':
                self.setQuitOnLastWindowClosed(new_values[name] == 'True')
            elif name == 'Application.theme' or 'Application.font_' in name:
                request_ui_refresh = True
            elif name == 'Application.check_updates':
                if new_values[name] == 'True':
                    self._version_timer.schedule(2000, self.check_version, None, True)
            elif name.startswith('Logger.'):
                request_logger_change = True

        if request_ui_refresh:
            logger.debug(f'Refreshing theme and fonts twice because of a setting change')
            self.refresh_theme_and_fonts()
            # With Qt 6.7.x on Windows we need to do it twice, otherwise the
            # fonts apply only the next time we change the setting. It's a Qt bug.
            self.refresh_theme_and_fonts()

        if request_new_source:
            logger.debug(f'Requesting new source because of a setting change')
            # We've already closed the old one in BeforeSettingsChanged handler
            self._source_holder.request_new_source()

        if request_logger_change:
            logger.debug(f'Reinitializing the logger because of a setting change')
            self._initialize_logger()

    def is_another_instance_running(self) -> bool:
        server = QTcpServer(self)
        server.setMaxPendingConnections(0)
        if server.listen(QHostAddress.SpecialAddress.Any, 11501):
            logger.debug(f'Could create a TCP listener on port {server.serverPort()}')
            return False
        else:
            return True

    def show_settings_dialog(self):
        SettingsDialog(
            self.activeWindow(),  # TODO: To avoid that... shall we make all those functions part of the main window?
            self._settings,
            {
                'FileEventSource.repair': self.repair_file_event_source,
                'FileEventSource.compress': self.compress_file_event_source,
                'Application.eyecandy_gradient_generate': self.generate_gradient,
                'WebsocketEventSource.authenticate': self.sign_in,
                'WebsocketEventSource.logout': self.sign_out,
                'WebsocketEventSource.delete_account': self.delete_account,
            }).show()

    def repair_file_event_source(self, _, callback: Callable) -> bool:
        if QMessageBox().warning(self.activeWindow(),
                                 "Confirmation",
                                 f"Are you sure you want to repair the data source? "
                                 f"This action will\n"
                                 f"1. Reorder operations according to their timestamps,\n"
                                 f"2. Remove duplicates,\n"
                                 f"3. Create missing data entities like users and backlogs, on first reference,\n"
                                 f"4. Renumber / reindex data,\n"
                                 f"5. Remove any events, which fail after 2 -- 4,\n"
                                 f"6. Create a backup file and overwrite the original data source one,\n"
                                 f"7. Display a detailed log of what it did.\n"
                                 f"\n"
                                 f"If there are no errors, then this action won't create or overwrite any files.",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel) \
                == QMessageBox.StandardButton.Ok:
            cast: FileEventSource = self._source_holder.get_source()
            log = cast.repair()
            if 'No changes were made' in log[-1]:
                # Reload the source
                self._source_holder.close_current_source()
                self._source_holder.request_new_source()
            QInputDialog.getMultiLineText(None,
                                          "Repair completed",
                                          "Please save this log for future reference. "
                                          "You can find all new items by searching (CTRL+F) for [Repaired] string.",
                                          "\n".join(log))
            return False

    def compress_file_event_source(self, _, callback: Callable) -> bool:
        if QMessageBox().warning(self.activeWindow(),
                                 "Confirmation",
                                 f"Are you sure you want to compress the data source? "
                                 f"This action will\n"
                                 f"1. Recreate the strategies based on the current data that you see,\n"
                                 f"2. Update timestamps with the latest modification date/time,\n"
                                 f"3. Renumber / reindex data,\n"
                                 f"4. Remove anything that you deleted,\n"
                                 f"5. Create a backup file and overwrite the original data source one,\n"
                                 f"6. Display a detailed log of what it did.\n"
                                 f"\n"
                                 f"As a result you will still see the same data as you do now, but the underlying "
                                 f"history might be lost. This might affect statistics and any other features relying "
                                 f"on detailed historical data.\n\n"
                                 f"We recommend using this feature only if your loading times became uncomfortably "
                                 f"long, or if you deleted something and want it to be gone forever.",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel) \
                == QMessageBox.StandardButton.Ok:
            cast: FileEventSource = self._source_holder.get_source()
            log = cast.compress()
            if 'No changes were made' in log[-1]:
                # Reload the source
                self._source_holder.close_current_source()
                self._source_holder.request_new_source()
            QInputDialog.getMultiLineText(None,
                                          "The file is compressed",
                                          None,
                                          "\n".join(log))
            return False

    def delete_account(self, _, callback: Callable) -> bool:
        source = self._source_holder.get_source()
        if not source.can_connect() or not self.get_heartbeat().is_online():
            QMessageBox().warning(self.activeWindow(),
                                  'No connection',
                                  'To perform this operation you must be logged in and online.',
                                  QMessageBox.StandardButton.Ok)
            return False
        (test, ok) = QInputDialog.getText(self.activeWindow(),
                                          'Confirmation',
                                          'Are you sure you want to delete your account? This will erase all\n'
                                          'traces of your user on this server. This operation cannot be undone.\n'
                                          'Export your data before doing it.\n\n'
                                          'Type "delete" below to confirm.',
                                          text='')
        if ok:
            if test.lower() == 'delete':
                source.execute(DeleteAccountStrategy, [''])
                # Avoid re-creating this account immediately
                source.set_config_parameters({'WebsocketEventSource.consent': 'False'})
                callback('WebsocketEventSource.consent', 'False')
                return True  # Close Settings dialog
            else:
                QMessageBox().information(self.activeWindow(),
                                          'Canceled',
                                          'You should\'ve typed "delete", canceling account deletion.',
                                          QMessageBox.StandardButton.Ok)
        return False

    def generate_gradient(self, _, callback: Callable) -> bool:
        preset_names = [preset.name for preset in QGradient.Preset]
        if 'NumPresets' in preset_names:
            preset_names.remove('NumPresets')
        chosen = secrets.choice(preset_names)
        self._settings.set({'Application.eyecandy_gradient': chosen})
        callback('Application.eyecandy_gradient', chosen)
        return False

    def sign_in(self, _, callback: Callable) -> bool:
        def save(auth: AuthenticationRecord):
            self._settings.set({
                'WebsocketEventSource.auth_type': 'google',
                'WebsocketEventSource.username': auth.email,
                'WebsocketEventSource.consent': 'False',
                'WebsocketEventSource.refresh_token!': auth.refresh_token,
            })
            callback('WebsocketEventSource.auth_type', 'google')
            callback('WebsocketEventSource.username', auth.email)
            callback('WebsocketEventSource.consent', 'False')
            callback('WebsocketEventSource.refresh_token!', auth.refresh_token)
            callback('WebsocketEventSource.logout', f'Sign out <{auth.email}>')
        authenticate(self, save)
        return False

    def sign_out(self, _, callback: Callable) -> bool:
        self._settings.set({
            'WebsocketEventSource.auth_type': 'google',
            'WebsocketEventSource.username': 'user@local.host',
            'WebsocketEventSource.consent': 'False',
            'WebsocketEventSource.refresh_token!': '',
        })
        callback('WebsocketEventSource.auth_type', 'google')
        callback('WebsocketEventSource.username', 'user@local.host')
        callback('WebsocketEventSource.consent', 'False')
        callback('WebsocketEventSource.refresh_token!', '')
        callback('WebsocketEventSource.logout', f'Sign out')
        return False

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('application.settings', "Settings", 'F10', None, Application.show_settings_dialog)
        actions.add('application.quit', "Quit", 'Ctrl+Q', None, Application.quit_local)
        actions.add('application.import', "Import data...", 'Ctrl+I', None, Application.show_import_wizard)
        actions.add('application.export', "Export data...", 'Ctrl+E', None, Application.show_export_wizard)
        actions.add('application.about', "About", '', None, Application.show_about)
        actions.add('application.toolbar', "Show toolbar", '', None, Application.toggle_toolbar, True, True)
        actions.add('application.stats', "Pomodoro health", 'F9', None, Application.show_stats)
        actions.add('application.workSummary', "Work summary", 'F3', None, Application.show_work_summary)

        def contact(url: str) -> Callable:
            return lambda _: open_url(url)
        actions.add('application.contactGithub', "GitHub", '', None, contact('https://github.com/flowkeeper-org/fk-desktop/issues'))
        actions.add('application.contactDiscord', "Discord", '', None, contact('https://discord.gg/SJfrsvgfmf'))
        actions.add('application.contactReddit', "Reddit", '', None, contact('https://www.reddit.com/r/Flowkeeper'))
        actions.add('application.contactLinkedIn', "LinkedIn", '', None, contact('https://www.linkedin.com/company/flowkeeper-org'))
        actions.add('application.contactTelegram', "Telegram", '', None, contact('https://t.me/flowkeeper_org'))
        actions.add('application.contactEmail', "Email", '', None, contact('mailto:contact@flowkeeper.org'))

    def quit_local(self):
        Application.quit()

    def show_import_wizard(self):
        ImportWizard(self._source_holder,
                     self.activeWindow()).show()

    def show_export_wizard(self):
        ExportWizard(self._source_holder.get_source(),
                     self.activeWindow()).show()

    def show_about(self):
        AboutWindow(self.activeWindow()).show()

    def toggle_toolbar(self, state: bool):
        self._settings.set({ 'Application.show_toolbar': str(state) })

    def get_heartbeat(self) -> Heartbeat:
        return self._heartbeat

    def check_version(self, event: str, when: datetime.datetime | None = None) -> None:
        def on_version(latest: Version, changelog: str):
            if latest is not None:
                if latest > self._current_version:
                    self._emit(NewReleaseAvailable, {
                        'current': self._current_version,
                        'latest': latest,
                        'changelog': changelog,
                    })
                else:
                    logger.debug(f'We are on the latest Flowkeeper version already (current is {self._current_version}, latest is {latest})')
            else:
                logger.warning("Couldn't get the latest release info from GitHub")
        logger.debug('Will check GitHub releases for the latest version')
        get_latest_version(self, on_version)

    def show_stats(self, event: str = None) -> None:
        StatsWindow(self.activeWindow(),
                    self.get_header_font(),
                    self.get_theme_variables(),
                    self._source_holder.get_source()).show()

    def show_work_summary(self, event: str = None) -> None:
        WorkSummaryWindow(self.activeWindow(), self._source_holder.get_source()).show()

    def on_new_version(self, event: str, current: Version, latest: Version, changelog: str) -> None:
        ignored = self._settings.get('Application.ignored_updates').split(',')
        latest_str = str(latest)
        if latest_str in ignored:
            logger.debug(f'An updated version {latest_str} is available, but the user chose to ignore it')
            return
        msg = QMessageBox(QMessageBox.Icon.Information,
                          "An update is available",
                          f"You currently use Flowkeeper {current}. A newer version {latest_str} is now available at "
                          f"flowkeeper.org. Would you like to download it? "
                          f'[More...](https://flowkeeper.org/v{latest_str}/)',
                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                          self.activeWindow())
        msg.setDetailedText(changelog)
        msg.setTextFormat(Qt.TextFormat.MarkdownText)
        check = QCheckBox("Ignore this update", msg)
        msg.setCheckBox(check)
        res = msg.exec()
        if check.isChecked():
            ignored.append(latest_str)
            self._settings.set({'Application.ignored_updates': ','.join(ignored)})
        if res == QMessageBox.StandardButton.Yes:
            webbrowser.open(f"https://flowkeeper.org/#download")

    def is_dark_theme(self):
        bg_color_str = self.get_theme_variables()['PRIMARY_BG_COLOR']
        return QColor(bg_color_str).lightness() < 128

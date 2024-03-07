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
import random
import sys
import traceback
import urllib
import webbrowser

from PySide6.QtCore import QFile
from PySide6.QtGui import QFont, QFontMetrics, QGradient
from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.events import AfterSettingChanged, SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.tenant import Tenant
from fk.desktop.export_wizard import ExportWizard
from fk.desktop.import_wizard import ImportWizard
from fk.desktop.settings import SettingsDialog
from fk.qt.about_window import AboutWindow
from fk.qt.actions import Actions
from fk.qt.heartbeat import Heartbeat
from fk.qt.qt_filesystem_watcher import QtFilesystemWatcher
from fk.qt.qt_invoker import invoke_in_main_thread
from fk.qt.qt_settings import QtSettings
from fk.qt.threaded_event_source import ThreadedEventSource
from fk.qt.websocket_event_source import WebsocketEventSource

AfterFontsChanged = "AfterFontsChanged"
AfterSourceChanged = "AfterSourceChanged"


class Application(QApplication, AbstractEventEmitter):
    _settings: AbstractSettings
    _font_main: QFont
    _font_header: QFont
    _row_height: int
    _source: AbstractEventSource | None
    _heartbeat: Heartbeat

    def __init__(self, args: [str]):
        super().__init__(args,
                         allowed_events=[AfterFontsChanged, AfterSourceChanged],
                         callback_invoker=invoke_in_main_thread)

        self._heartbeat = None
        sys.excepthook = self.on_exception

        # It's important to initialize settings after the QApplication
        # has been constructed, as it uses default QFont and other
        # OS-specific values
        self._settings = QtSettings()
        self._settings.on(AfterSettingChanged, self._on_setting_changed)

        # Quit app on close
        quit_on_close = (self._settings.get('Application.quit_on_close') == 'True')
        self.setQuitOnLastWindowClosed(quit_on_close)

        self.set_theme(self._settings.get('Application.theme'))

        # Fonts, styles, etc.
        self._initialize_fonts()
        self._row_height = self._auto_resize()

        self._source = None
        self._recreate_source()

    def _on_went_offline(self, event, after: int, last_received: datetime.datetime) -> None:
        # TODO -- lock the UI
        print(f'WARNING - We detected that the client went offline after {after}ms')
        print(f'          Last time we heard from the server was {last_received}')

    def _on_went_online(self, event, ping: int) -> None:
        # TODO -- unlock the UI
        print(f'We are (back) online with the roundtrip delay of {ping}ms')

    def _recreate_source(self):
        source_type = self._settings.get('Source.type')
        root = Tenant(self._settings)
        source: AbstractEventSource
        if source_type == 'local':
            inner_source = FileEventSource(self._settings, root, QtFilesystemWatcher())
            source = ThreadedEventSource(inner_source)
        elif source_type in ('websocket', 'flowkeeper.org', 'flowkeeper.pro'):
            source = WebsocketEventSource(self._settings, root)
            if self._heartbeat is not None:
                self._heartbeat.stop()
            self._heartbeat = Heartbeat(source, 3000, 500)
            self._heartbeat.on(events.WentOffline, self._on_went_offline)
            self._heartbeat.on(events.WentOnline, self._on_went_online)
        else:
            raise Exception(f"Source type {source_type} not supported")

        # Unsubscribe everyone from the orphan source, so that we don't receive double events
        if self._source is not None:
            self._source.cancel('*')
            self._source.disconnect()
        self._source = source

        self._emit(AfterSourceChanged, {
            'source': source
        })

    def get_settings(self):
        return self._settings

    def get_source(self):
        return self._source

    # noinspection PyUnresolvedReferences
    def set_theme(self, theme: str):
        # Apply CSS
        import fk.desktop.theme_common
        if theme == 'light':
            import fk.desktop.theme_light
        elif theme == 'dark':
            import fk.desktop.theme_dark
        elif theme == 'mixed':
            import fk.desktop.theme_mixed

        # TODO: Can't change this on the fly
        f = QFile(":/style.qss")
        f.open(QFile.OpenModeFlag.ReadOnly)
        self.setStyleSheet(f.readAll().toStdString())
        f.close()

        print('Stylesheet loaded')

    def _initialize_fonts(self) -> (QFont, QFont):
        self._font_header = QFont(self._settings.get('Application.font_header_family'),
                                  int(self._settings.get('Application.font_header_size')))
        if self._font_header is None:
            self._font_header = QFont()
            self._font_header.setPointSize(int(self._font_header.pointSize() * 24.0 / 9))
    
        self._font_main = QFont(self._settings.get('Application.font_main_family'),
                                int(self._settings.get('Application.font_main_size')))
        if self._font_main is None:
            self._font_main = QFont()

        self.setFont(self._font_main)
        self._emit(AfterFontsChanged, {
            'main_font': self._font_main,
            'header_font': self._font_header,
            'application': self
        })

    def _auto_resize(self) -> int:
        h: int = QFontMetrics(self._font_main).height() + 8
        # users_table.verticalHeader().setDefaultSectionSize(h)
        # backlogs_table.verticalHeader().setDefaultSectionSize(h)
        # workitems_table.verticalHeader().setDefaultSectionSize(h)
        # Save it to Settings, so that we can use this value when
        # calculating display hints for the Pomodoro Delegate.
        # As of now, this requires app restart to apply.
        self._settings.set('Application.table_row_height', str(h))
        return h

    def restart_warning(self) -> None:
        QMessageBox().warning(self.activeWindow(),
                              "Restart required",
                              f"Please restart Flowkeeper to apply new settings",
                              QMessageBox.StandardButton.Ok)

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        print("Exception", to_log)
        if (QMessageBox().critical(self.activeWindow(),
                                   "Unexpected error",
                                   f"{exc_type.__name__}: {exc_value}\nWe will appreciate it if you click Open to report it on GitHub.",
                                   QMessageBox.StandardButton.Ok,
                                   QMessageBox.StandardButton.Open)
                == QMessageBox.StandardButton.Open):
            params = urllib.parse.urlencode({
                'labels': 'exception',
                'title': f'Unhandled {exc_type.__name__}',
                'body': f'PLEASE PROVIDE SOME DETAILS HERE.\nREVIEW THE BELOW PART FOR SENSITIVE DATA.\n\n```\n{to_log}```'
            })
            webbrowser.open(f"https://github.com/flowkeeper-org/fk-desktop/issues/new?{params}")

    def get_main_font(self):
        return self._font_main

    def get_header_font(self):
        return self._font_header

    def get_row_height(self):
        return self._row_height

    def _on_setting_changed(self, event: str, name: str, old_value: str, new_value: str):
        # print(f'Setting {name} changed from {old_value} to {new_value}')
        if name == 'Source.type' or name.startswith('WebsocketEventSource.') or name.startswith('FileEventSource.'):
            self._recreate_source()
            self._source.start()
        elif name == 'Application.quit_on_close':
            self.setQuitOnLastWindowClosed(new_value == 'True')
        elif 'Application.font_' in name:
            self._initialize_fonts()
        elif name == 'Application.theme':
            self.restart_warning()
            # app.set_theme(new_value)
        # TODO: Subscribe to sound settings
        # TODO: Subscribe the sources to the settings they use
        # TODO: Reload the app when the source changes
        # TODO: Recreate the source

    def show_settings_dialog(self):
        SettingsDialog(self._settings, {
            'FileEventSource.repair': self.repair_file_event_source,
            'Application.eyecandy_gradient_generate': self.generate_gradient,
            'WebsocketEventSource.authenticate': self.sign_in,
        }).show()

    def repair_file_event_source(self, _):
        if QMessageBox().warning(self.activeWindow(),
                                 "Confirmation",
                                 f"Are you sure you want to repair the data source? "
                                 f"This action will\n"
                                 f"1. Remove duplicates,\n"
                                 f"2. Create missing data entities like users and backlogs, on first reference,\n"
                                 f"3. Renumber / reindex data,\n"
                                 f"4. Remove any events, which fail after 1 -- 3,\n"
                                 f"5. Create a backup file and overwrite the original data source one,\n"
                                 f"6. Display a detailed log of what it did.\n"
                                 f"\n"
                                 f"If there are no errors, then this action won't create or overwrite any files.",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel) \
                == QMessageBox.StandardButton.Ok:
            cast: FileEventSource = self._source
            log = cast.repair()
            QInputDialog.getMultiLineText(None,
                                          "Repair completed",
                                          "Please save this log for future reference. "
                                          "You can find all new items by searching (CTRL+F) for [Repaired] string.\n"
                                          "Flowkeeper restart is required to reload the changes.",
                                          "\n".join(log))

    def generate_gradient(self, _):
        chosen = random.choice(list(QGradient.Preset))
        self._settings.set('Application.eyecandy_gradient', chosen.name)

    def sign_in(self, _):
        self._settings.set('WebsocketEventSource.token', '123')

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('application.settings', "Settings", 'F10', None, Application.show_settings_dialog)
        actions.add('application.quit', "Quit", 'Ctrl+Q', None, Application.quit_local)
        actions.add('application.import', "Import...", 'Ctrl+I', None, Application.show_import_wizard)
        actions.add('application.export', "Export...", 'Ctrl+E', None, Application.show_export_wizard)
        actions.add('application.about', "About", '', None, Application.show_about)

    def quit_local(self):
        Application.quit()

    def show_import_wizard(self):
        ImportWizard(self._source,
                     self.activeWindow()).show()

    def show_export_wizard(self):
        ExportWizard(self._source,
                     self.activeWindow()).show()

    def show_about(self):
        AboutWindow(self.activeWindow()).show()

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
import sys
import traceback
import urllib
import webbrowser

from PySide6.QtCore import QFile
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QMessageBox

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.events import AfterSettingChanged, SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.tenant import Tenant
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

    def __init__(self, args: [str]):
        super().__init__(args,
                         allowed_events=[AfterFontsChanged, AfterSourceChanged],
                         callback_invoker=invoke_in_main_thread)

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

    def _recreate_source(self):
        source_type = self._settings.get('Source.type')
        root = Tenant(self._settings)
        source: AbstractEventSource
        if source_type == 'local':
            inner_source = FileEventSource(self._settings, root, QtFilesystemWatcher())
            source = ThreadedEventSource(inner_source)
        elif source_type in ('websocket', 'flowkeeper.org', 'flowkeeper.pro'):
            source = WebsocketEventSource(self._settings, root)
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
        h: int = QFontMetrics(QFont()).height() + 8
        # Save it to Settings, so that we can use this value when
        # calculating display hints for the Pomodoro Delegate.
        # As of now, this requires app restart to apply.
        self._settings.set('Application.table_row_height', str(h))
        return h

    def restart_warning(self) -> None:
        QMessageBox().warning(self,
                            "Restart required",
                            f"Please restart Flowkeeper to apply new settings",
                            QMessageBox.StandardButton.Ok)

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        print("Exception", to_log)
        if (QMessageBox().critical(None,
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

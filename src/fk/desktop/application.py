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
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QTextEdit, QMessageBox

from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_settings import QtSettings


class Application(QApplication):
    _settings: AbstractSettings
    _font_main: QFont
    _font_header: QFont
    _row_height: int

    def __init__(self, args: [str]):
        super().__init__(args)

        sys.excepthook = self.on_exception

        # It's important to initialize settings after the QApplication
        # has been constructed, as it uses default QFont and other
        # OS-specific values
        self._settings = QtSettings()

        # Quit app on close
        quit_on_close = (self._settings.get('Application.quit_on_close') == 'True')
        self.setQuitOnLastWindowClosed(quit_on_close)

        self.set_theme(self._settings.get('Application.theme'))

        # Fonts, styles, etc.
        self._font_main, self._font_header = self._initialize_fonts()
        self._row_height = self._auto_resize()

    def get_settings(self):
        return self._settings

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
        font_header = QFont(self._settings.get('Application.font_header_family'),
                            int(self._settings.get('Application.font_header_size')))
        if font_header is None:
            font_header = QFont()
            font_header.setPointSize(int(font_header.pointSize() * 24.0 / 9))
    
        font_main = QFont(self._settings.get('Application.font_main_family'),
                          int(self._settings.get('Application.font_main_size')))
        if font_main is None:
            font_main = QFont()
    
        self.setFont(font_main)
        return font_main, font_header

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

    def on_setting_changed(self, event: str, name: str, old_value: str, new_value: str):
        # print(f'Setting {name} changed from {old_value} to {new_value}')
        status.showMessage('Settings changed')
        if name == 'Source.type':
            restart_warning()
        elif name == 'Application.timer_ui_mode' and (pomodoro_timer.is_working() or pomodoro_timer.is_resting()):
            # TODO: This really doesn't work well
            hide_timer_automatically(None)
            show_timer_automatically()
        elif name == 'Application.quit_on_close':
            app.setQuitOnLastWindowClosed(new_value == 'True')
        elif 'Application.font_' in name:
            initialize_fonts(settings)
        elif name == 'Application.show_main_menu':
            main_menu.setVisible(new_value == 'True')
        elif name == 'Application.show_status_bar':
            status.setVisible(new_value == 'True')
        elif name == 'Application.show_toolbar':
            toolbar.setVisible(new_value == 'True')
        elif name == 'Application.show_left_toolbar':
            left_toolbar.setVisible(new_value == 'True')
        elif name == 'Application.show_tray_icon':
            tray.setVisible(new_value == 'True')
        elif name == 'Application.header_background':
            eye_candy()
        elif name == 'Application.theme':
            restart_warning()
            # app.set_theme(new_value)
        elif name.startswith('WebsocketEventSource.'):
            source.start()
        # TODO: Subscribe to sound settings
        # TODO: Subscribe the sources to the settings they use
        # TODO: Reload the app when the source changes

    def show_about(self):
        loader = QUiLoader()

        # Load main window
        file = QFile(":/about.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        about_window: QMainWindow = loader.load(file, None)
        file.close()

        # noinspection PyTypeChecker
        about_version: QLabel = about_window.findChild(QLabel, "version")
        file = QFile(":/VERSION.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_version.setText(file.readAll().toStdString())
        file.close()

        # noinspection PyTypeChecker
        about_changelog: QTextEdit = about_window.findChild(QTextEdit, "notes")
        file = QFile(":/CHANGELOG.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_changelog.setMarkdown(file.readAll().toStdString())
        file.close()

        # noinspection PyTypeChecker
        about_credits: QTextEdit = about_window.findChild(QTextEdit, "credits")
        file = QFile(":/CREDITS.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_credits.setMarkdown(file.readAll().toStdString())
        file.close()

        # noinspection PyTypeChecker
        about_license: QTextEdit = about_window.findChild(QTextEdit, "license")
        file = QFile(":/LICENSE.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_license.setMarkdown(file.readAll().toStdString())
        file.close()

        about_window.show()

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        if (QMessageBox().critical(self,
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

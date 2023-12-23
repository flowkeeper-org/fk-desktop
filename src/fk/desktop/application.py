from PySide6.QtCore import QFile
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from fk.core.abstract_settings import AbstractSettings
from fk.core.path_resolver import resolve_path

import fk.desktop.theme_common
from fk.qt.qt_settings import QtSettings


class Application(QApplication):
    _settings: AbstractSettings
    
    def __init__(self, args: [str]):
        super().__init__(args)

        # It's important to initialize settings after the QApplication
        # has been constructed, as it uses default QFont and other
        # OS-specific values
        self._settings = QtSettings()

        # Quit app on close
        quit_on_close = (self._settings.get('Application.quit_on_close') == 'True')
        self.setQuitOnLastWindowClosed(quit_on_close)

        self.set_theme(self._settings.get('Application.theme'))

    def get_settings(self):
        return self._settings

    def on_settings_change(self):
        pass

    def set_theme(self, theme: str):
        # Apply CSS
        if theme == 'light':
            import fk.desktop.theme_light
        elif theme == 'dark':
            import fk.desktop.theme_dark

        # TODO: Can't change this on the fly
        f = QFile(":/style.qss")
        f.open(QFile.OpenModeFlag.ReadOnly)
        self.setStyleSheet(f.readAll().toStdString())
        f.close()

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
from PySide6 import QtUiTools
from PySide6.QtCore import QFile, QObject
from PySide6.QtWidgets import QWidget, QLabel, QTextEdit, QMainWindow

from fk.qt.app_version import get_current_version


class AboutWindow(QObject):
    _about_window: QMainWindow

    def __init__(self, parent: QWidget | None):
        super().__init__(parent)
        file = QFile(":/about.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._about_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

    def show(self):
        # noinspection PyTypeChecker
        about_version: QLabel = self._about_window.findChild(QLabel, "version")
        about_version.setText(str(get_current_version()))

        # noinspection PyTypeChecker
        about_changelog: QTextEdit = self._about_window.findChild(QTextEdit, "notes")
        file = QFile(":/CHANGELOG.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_changelog.setMarkdown(file.readAll().toStdString())
        file.close()

        # noinspection PyTypeChecker
        about_credits: QTextEdit = self._about_window.findChild(QTextEdit, "credits")
        file = QFile(":/CREDITS.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_credits.setMarkdown(file.readAll().toStdString())
        file.close()

        # noinspection PyTypeChecker
        about_license: QTextEdit = self._about_window.findChild(QTextEdit, "license")
        file = QFile(":/LICENSE.txt")
        file.open(QFile.OpenModeFlag.ReadOnly)
        about_license.setMarkdown(file.readAll().toStdString())
        file.close()

        self._about_window.show()



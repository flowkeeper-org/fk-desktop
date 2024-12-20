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

from PySide6 import QtUiTools
from PySide6.QtCore import QFile, QObject
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QWidget, QLabel, QTextEdit, QMainWindow

from fk.core.abstract_timer import AbstractTimer
from fk.qt.app_version import get_current_version
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer
from fk.qt.qt_timer import QtTimer


class AboutWindow(QObject):
    _about_window: QMainWindow
    _timer_display: MinimalTimerRenderer
    _timer: AbstractTimer
    _tick: int

    def __init__(self, parent: QWidget | None):
        super().__init__(parent)
        self._timer_display = None
        self._timer = QtTimer('About window')
        self._tick = 299

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

        # noinspection PyTypeChecker
        about_icon: QLabel = self._about_window.findChild(QLabel, "icon")
        about_icon.setFixedWidth(150)
        about_icon.setFixedHeight(150)
        bg_color = about_icon.palette().color(QPalette.ColorRole.Base)
        fg_color = about_icon.palette().color(QPalette.ColorRole.Text)
        self._timer_display = MinimalTimerRenderer(about_icon,
                                                   bg_color,
                                                   fg_color)
        about_icon.installEventFilter(self._timer_display)
        self._timer_display.setObjectName('AboutWindowRenderer')
        self._timer_display.reset()
        self._timer.schedule(100, self._handle_tick, None)
        self._handle_tick(None, None)

        self._about_window.show()

    def _handle_tick(self, params: dict | None, when: datetime.datetime | None = None) -> None:
        self._timer_display.set_values(self._tick, 300, None, None, 'working')
        self._timer_display.repaint()
        self._tick -= 1
        if self._tick < 0:
            self._tick = 299

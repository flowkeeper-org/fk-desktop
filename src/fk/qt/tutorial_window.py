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
from PySide6.QtCore import QFile, QObject, QRegularExpression
from PySide6.QtWidgets import QWidget, QMainWindow, QStackedWidget, QPushButton

from fk.core.abstract_settings import AbstractSettings


class TutorialWindow(QObject):
    _tutorial_window: QMainWindow
    _pages: QStackedWidget
    _previous_button: QPushButton
    _next_button: QPushButton
    _count: int
    _settings: AbstractSettings

    def __init__(self, parent: QWidget | None, settings: AbstractSettings):
        super().__init__(parent)
        self._settings = settings
        file = QFile(":/tutorial.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        self._tutorial_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()
        self._pages = self._tutorial_window.findChild(QStackedWidget, "pages")
        self._previous_button = self._tutorial_window.findChild(QPushButton, "previous")
        self._previous_button.setHidden(True)
        self._previous_button.clicked.connect(self._on_previous)
        self._next_button = self._tutorial_window.findChild(QPushButton, "next")
        self._next_button.clicked.connect(self._on_next)
        self._count = len(self._pages.findChildren(QWidget, QRegularExpression('page.+')))

    def _update_page(self, new_index: int):
        self._pages.setCurrentIndex(new_index)
        self._previous_button.setHidden(new_index <= 0)
        if new_index > self._count - 1:
            self._settings.set({'Application.show_tutorial': 'False'})
            self._tutorial_window.close()
        elif new_index == self._count - 1:
            self._next_button.setText('Close')
        else:
            self._next_button.setText('Next >')

    def _on_previous(self):
        self._update_page(self._pages.currentIndex() - 1)

    def _on_next(self):
        self._update_page(self._pages.currentIndex() + 1)

    def show(self):
        self._tutorial_window.show()

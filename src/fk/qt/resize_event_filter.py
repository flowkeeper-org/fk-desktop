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
from PySide6.QtCore import QObject, QEvent, QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QWidget, QMainWindow, QSplitter

from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_timer import QtTimer


class ResizeEventFilter(QMainWindow):
    _window: QMainWindow
    _timer: QtTimer
    _is_resizing: bool
    _settings: AbstractSettings
    _main_layout: QWidget
    _splitter: QSplitter

    def __init__(self,
                 window: QMainWindow,
                 main_layout: QWidget,
                 settings: AbstractSettings):
        super().__init__()
        self._window = window
        self._settings = settings
        self._main_layout = main_layout
        self._timer = QtTimer("Window resizing")
        self._is_resizing = False

        # Splitter
        # noinspection PyTypeChecker
        self._splitter = window.findChild(QSplitter, "splitter")
        self._splitter.splitterMoved.connect(self.save_splitter_size)

        self.restore_size()

    def resize_completed(self):
        self._is_resizing = False
        if not self._main_layout.isVisible():  # Avoid saving window size in Timer mode
            return
        # We'll check against the old value to avoid resize loops and spurious setting change events
        new_width = self._window.size().width()
        new_height = self._window.size().height()
        old_width = int(self._settings.get('Application.window_width'))
        old_height = int(self._settings.get('Application.window_height'))
        if old_width != new_width or old_height != new_height:
            self._settings.set({
                'Application.window_width': str(new_width),
                'Application.window_height': str(new_height),
            })

    def eventFilter(self, widget: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and isinstance(event, QResizeEvent):
            if widget == self._window:
                if self._is_resizing:   # Don't fire those events too frequently
                    return False
                self._timer.schedule(1000,
                                     lambda _1, _2: self.resize_completed(),
                                     None,
                                     True)
                self._is_resizing = True
        return False

    def restore_size(self) -> None:
        w = int(self._settings.get('Application.window_width'))
        h = int(self._settings.get('Application.window_height'))
        splitter_width = int(self._settings.get('Application.window_splitter_width'))
        self._splitter.setSizes([splitter_width, w - splitter_width])
        self._window.resize(QSize(w, h))

    def save_splitter_size(self, new_width: int, index: int) -> None:
        old_width = int(self._settings.get('Application.window_splitter_width'))
        if old_width != new_width:
            self._settings.set({'Application.window_splitter_width': str(new_width)})

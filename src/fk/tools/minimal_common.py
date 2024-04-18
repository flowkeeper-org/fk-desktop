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
from typing import Callable

from PySide6.QtWidgets import QMainWindow

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import AfterSourceChanged
from fk.core.events import SourceMessagesProcessed
from fk.desktop.application import Application
from fk.qt.actions import Actions


class MinimalCommon:
    _app: Application
    _window: QMainWindow
    _actions: Actions
    _source: AbstractEventSource
    _settings: AbstractSettings
    _callback: Callable
    _initialize_source: bool

    def main_loop(self):
        self._app.setQuitOnLastWindowClosed(True)
        self._window.show()

        try:
            print(f'MinimalCommon: Entering main_loop: {self._source} / {self._initialize_source}')
            if self._initialize_source:
                print('MinimalCommon: Request source initialization')
                self._app.initialize_source()
        except Exception as ex:
            self._app.on_exception(type(ex), ex, ex.__traceback__)

        sys.exit(self._app.exec())

    def _on_messages(self, event: str, source: AbstractEventSource) -> None:
        print(f'MinimalCommon: Will call {self._callback}')
        self._callback(source.get_data())

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        print(f'MinimalCommon: _on_source_changed({source})')
        self._source = source
        if self._callback is not None:
            source.on(SourceMessagesProcessed, self._on_messages)

    def __init__(self, callback: Callable = None, initialize_source: bool = True):
        self._source = None
        self._callback = callback
        self._initialize_source = initialize_source
        self._app = Application(sys.argv)
        self._app.setQuitOnLastWindowClosed(True)
        self._settings = self._app.get_settings()
        self._window = QMainWindow()
        self._actions = Actions(self._window, self._settings)
        Application.define_actions(self._actions)
        self._actions.bind('application', self._app)
        self._app.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def get_actions(self):
        return self._actions

    def get_app(self):
        return self._app

    def get_settings(self):
        return self._settings

    def get_window(self):
        return self._window

    def get_source(self):
        return self._source

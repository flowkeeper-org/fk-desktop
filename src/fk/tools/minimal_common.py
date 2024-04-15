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
from fk.core.event_source_holder import AfterSourceChanged
from fk.core.events import SourceMessagesProcessed
from fk.desktop.application import Application
from fk.qt.actions import Actions

app = Application(sys.argv)
app.setQuitOnLastWindowClosed(True)
settings = app.get_settings()

window = QMainWindow()
actions = Actions(window, settings)
Application.define_actions(actions)
actions.bind('application', app)

_source: AbstractEventSource = None
_initialized: bool = False
_callback: Callable = None
_start_source: bool = False

def _on_source_changed(event: str, source: AbstractEventSource):
    global _source
    global _initialized
    global _callback
    _source = source
    if not _initialized:
        _initialized = True
        if _callback is not None:
            _source.on(SourceMessagesProcessed, lambda event: _callback())
        if _start_source:
            _source.start()


def main_loop(callback=None, start_source=True):
    global _initialized
    global _callback
    global _start_source
    _callback = callback
    _start_source = start_source
    app.setQuitOnLastWindowClosed(True)
    window.show()

    try:
        if _source is not None:
            _initialized = True
            if callback is not None:
                _source.on(SourceMessagesProcessed, lambda event: callback())
            if start_source:
                _source.start()
    except Exception as ex:
        app.on_exception(type(ex), ex, ex.__traceback__)

    sys.exit(app.exec())


app.get_source_holder().on(AfterSourceChanged, _on_source_changed)

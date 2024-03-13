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

from PySide6.QtWidgets import QMainWindow

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.tenant import Tenant
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.qt_filesystem_watcher import QtFilesystemWatcher
from fk.qt.threaded_event_source import ThreadedEventSource
from fk.qt.websocket_event_source import WebsocketEventSource

app = Application(sys.argv)
app.setQuitOnLastWindowClosed(True)
settings = app.get_settings()

source: AbstractEventSource
source_type = settings.get('Source.type')
root = Tenant(settings)
if source_type == 'local':
    source = ThreadedEventSource(FileEventSource(settings,
                                                 root,
                                                 QtFilesystemWatcher()))
elif source_type in ('websocket', 'flowkeeper.org', 'flowkeeper.pro'):
    source = WebsocketEventSource(settings, app, root)
else:
    raise Exception(f"Source type {source_type} not supported")

window = QMainWindow()
actions = Actions(window, settings)
Application.define_actions(actions)
actions.bind('application', app)


def main_loop(callback = None, start_source = True):
    app.setQuitOnLastWindowClosed(True)
    window.show()

    try:
        if callback is not None:
            source.on(SourceMessagesProcessed, lambda event: callback())
        if start_source:
            source.start()
    except Exception as ex:
        app.on_exception(type(ex), ex, ex.__traceback__)

    sys.exit(app.exec())

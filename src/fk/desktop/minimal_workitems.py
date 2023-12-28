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
from fk.core.app import App
from fk.core.events import SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.desktop.application import Application
from fk.qt.qt_filesystem_watcher import QtFilesystemWatcher
from fk.qt.threaded_event_source import ThreadedEventSource
from fk.qt.websocket_event_source import WebsocketEventSource
from fk.qt.workitem_tableview import WorkitemTableView

app = Application(sys.argv)
settings = app.get_settings()

source: AbstractEventSource
source_type = settings.get('Source.type')
root = App(settings)
if source_type == 'local':
    source = ThreadedEventSource(FileEventSource(settings,
                                                 root,
                                                 QtFilesystemWatcher()))
elif source_type in ('websocket', 'flowkeeper.org', 'flowkeeper.pro'):
    source = WebsocketEventSource(settings, root)
else:
    raise Exception(f"Source type {source_type} not supported")

window: QMainWindow = QMainWindow()
window.resize(600, 400)
workitems_table: WorkitemTableView = WorkitemTableView(window, source, dict())
window.setCentralWidget(workitems_table)

app.setQuitOnLastWindowClosed(True)
window.show()

try:
    source.on(SourceMessagesProcessed,
              lambda event: workitems_table.upstream_selected(
                  list(root.get_current_user().values())[0]
              ))
    source.start()
except Exception as ex:
    app.on_exception(type(ex), ex, ex.__traceback__)

sys.exit(app.exec())

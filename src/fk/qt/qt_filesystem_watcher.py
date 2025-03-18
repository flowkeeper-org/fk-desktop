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
from typing import Callable

from PySide6 import QtCore

from fk.core.abstract_filesystem_watcher import AbstractFilesystemWatcher


class QtFilesystemWatcher(AbstractFilesystemWatcher):
    _connections: dict[str, list[Callable]]
    _watcher: QtCore.QFileSystemWatcher

    def __init__(self):
        self._connections = dict()
        self._watcher = QtCore.QFileSystemWatcher()
        self._watcher.fileChanged.connect(lambda f: self._on_file_change(f))

    def watch(self, filename: str, callback: Callable[[str], None]):
        self._watcher.addPath(filename)
        if filename not in self._connections:
            self._connections[filename] = list()
        self._connections[filename].append(callback)

    def unwatch(self, filename: str) -> None:
        self._watcher.removePath(filename)
        del self._connections[filename]

    def unwatch_all(self) -> None:
        self._watcher.removePaths(self._watcher.files())
        self._connections.clear()

    def _on_file_change(self, filename: str) -> None:
        for callback in self._connections[filename]:
            callback(filename)

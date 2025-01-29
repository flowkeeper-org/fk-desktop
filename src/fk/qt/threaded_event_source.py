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
from __future__ import annotations

from typing import TypeVar

from PySide6.QtCore import QThreadPool, Slot

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_event_source_wrapper import AbstractEventSourceWrapper
from fk.qt.qt_invoker import invoke_in_main_thread
from fk.core.file_event_source import FileEventSource

TRoot = TypeVar('TRoot')


class ThreadedEventSource(AbstractEventSourceWrapper[TRoot]):
    _thread_pool: QThreadPool
    _application: 'Application'

    def __init__(self, wrapped: AbstractEventSource[TRoot], application: 'Application'):
        super().__init__(wrapped)
        self._thread_pool = QThreadPool()
        self._application = application

    def start(self, mute_events: bool = True, last_seq: int = 0) -> None:
        @Slot()
        def job():
            try:
                self._wrapped.start(mute_events, last_seq)
            except Exception as e:
                def fail(ex):
                    if type(ex) == IsADirectoryError and type(self._wrapped) == FileEventSource:
                        # Fixing #70 -- a rare case when the user selected a directory instead of a filename
                        self._application.bad_file_for_file_source()
                    else:
                        self._application.on_exception(type(ex), ex, ex.__traceback__)
                invoke_in_main_thread(fail, ex=e)
        self._thread_pool.start(job)

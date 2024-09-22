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

import logging
import os
import pickle
from pathlib import Path
from typing import TypeVar, Generic

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_event_source_wrapper import AbstractEventSourceWrapper
from fk.core.events import SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.tenant import Tenant

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class CachedData(Generic[TRoot]):
    data: TRoot
    last_seq: int

    def __init__(self, root: TRoot, last_seq: int):
        self.data = root
        self.last_seq = last_seq


class CachingEventSource(AbstractEventSourceWrapper[TRoot]):
    _application: 'Application'
    _redo_log: FileEventSource[Tenant]
    _redo_log_filename: str
    _cache_filename: str
    _last_seq_in_cache: int

    def __init__(self,
                 wrapped: AbstractEventSource[TRoot],
                 application: 'Application'):
        super().__init__(wrapped)
        self._application = application
        self._last_seq_in_cache = 0
        wrapped_id = self._wrapped.get_id()
        self._cache_filename = str(Path.home() / f'flowkeeper-cache-{wrapped_id}.bin')
        self._redo_log_filename = str(Path.home() / f'flowkeeper-redo-{wrapped_id}.txt')
        self.initialize_redo_log()
        self.on(SourceMessagesProcessed, self.on_messages)

    def on_messages(self, event: str, source: AbstractEventSource, carry: any = None):
        if carry != 'cache' and source == self._wrapped and source.get_last_sequence() != self._last_seq_in_cache:
            self.save_cache()

    def initialize_redo_log(self):
        filename = str(Path.home() / f'flowkeeper-redo-{self._wrapped.get_id()}.txt')
        user = self._application.get_settings().get_username()
        print(f'Initializing redo log with file {filename} and user {user}')
        settings = MockSettings(filename, user)
        self._redo_log = FileEventSource[Tenant](settings, NoCryptograph(settings), Tenant(settings))

    def restore_cache(self) -> int:
        """Returns the last sequence read"""
        print(f'Restoring data from cache: {self._cache_filename}')
        if os.path.isfile(self._cache_filename):
            with open(self._cache_filename, 'rb') as f:
                # TODO: This is crap
                cached: CachedData[TRoot] = pickle.load(f)
                self._wrapped._data = cached.data
                self._wrapped._data._settings = self.get_settings()
                self._last_seq_in_cache = cached.last_seq
                print(f'Restored.')
                return self._last_seq_in_cache
        print('Cache file not found')
        return 0

    def save_cache(self) -> None:
        print(f'Saving data to cache: {self._cache_filename}')
        with open(self._cache_filename, 'wb') as f:
            cached = CachedData(self.get_data(), self._wrapped.get_last_sequence())
            pickle.dump(cached, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f'Saved.')

    def start(self, mute_events: bool = True, last_seq: int = 0) -> None:
        restored_seq = self.restore_cache()
        if restored_seq > 0:
            self._wrapped._emit(events.SourceMessagesProcessed,
                       {'source': self._wrapped},
                       carry='cache')
            last_seq = restored_seq
            print(f'Emitted SourceMessagesProcessed from cache')
        self._wrapped.start(mute_events, last_seq)

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
from abc import ABC
from pathlib import Path
from typing import TypeVar, Generic

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.events import SourceMessagesProcessed, WentOnline
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


# This thing relies heavily on Python's super() semantics. To add caching to existing event sources,
# you need to create a new class like CachedWebsocketEventSource, which would inherit CachingMixin
# FIRST, and then the original event source class, e.g. WebsocketEventSource. When WebsocketEventSource
# calls self.foo(), Python delegates it to CachingMixin.foo(). To access WebsocketEventSource's
# foo() method, CachingMixin needs to use super().foo(). Also, for those mixins we got to be careful
# with method and field names to guarantee we don't override those form the "base" event source class.
class CachingMixin(AbstractEventSource[TRoot], ABC):
    _cache_application: 'Application'
    _redo_log: FileEventSource[Tenant]
    _redo_log_filename: str
    _cache_filename: str
    _last_seq_in_cache: int

    def __init__(self,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 application: 'Application',
                 root: TRoot):
        super().__init__(settings=settings,
                         cryptograph=cryptograph,
                         application=application,
                         root=root)
        self._cache_application = application
        self._last_seq_in_cache = 0
        # TODO: Use XDG way to get filenames (extract from Settings > File event source filename?)
        self._cache_filename = str(Path.home() / f'flowkeeper-cache-{super(CachingMixin, self).get_id()}.bin')
        self._redo_log_filename = str(Path.home() / f'flowkeeper-redo-{super(CachingMixin, self).get_id()}.txt')
        super(CachingMixin, self).on(SourceMessagesProcessed, self._save_cache)
        super(CachingMixin, self).on(WentOnline, self._send_redo_log)

    def _save_cache(self, event: str, source: AbstractEventSource, carry: any = None):
        if carry != 'cache' and source == self and source.get_last_sequence() != self._last_seq_in_cache:
            self.save_cache()

    def _initialize_redo_log_file(self):
        # This is done to avoid creating local user in the redo log
        if not os.path.isfile(self._redo_log_filename):
            with open(self._redo_log_filename, 'w', encoding='UTF-8'):
                pass

    def initialize_redo_log(self):
        user = self._cache_application.get_settings().get_username()
        logger.debug(f'Initializing redo log with file {self._redo_log_filename} and user {user}')
        self._initialize_redo_log_file()
        settings = MockSettings(self._redo_log_filename, user)
        self._redo_log = FileEventSource[Tenant](settings,
                                                 NoCryptograph(settings),
                                                 super(CachingMixin, self).get_data())

    def restore_cache(self) -> int:
        """Returns the last sequence read"""
        logger.debug(f'Restoring data from cache: {self._cache_filename}')
        if os.path.isfile(self._cache_filename):
            with open(self._cache_filename, 'rb') as f:
                cached: CachedData[TRoot] = pickle.load(f)
                super(CachingMixin, self).set_data(cached.data)
                super(CachingMixin, self).get_data()._settings = super(CachingMixin, self).get_settings()
                self._last_seq_in_cache = cached.last_seq
                logger.debug(f'Restored. Will auto-seal...')
                super(CachingMixin, self)._auto_seal_all()
                logger.debug(f'Auto-sealed.')
                return self._last_seq_in_cache
        logger.debug('Cache file not found')
        return 0

    def save_cache(self) -> None:
        if self._last_seq_in_cache != self.get_last_sequence():
            logger.debug(f'Saving data to cache: {self._cache_filename} / '
                         f'{self._last_seq_in_cache} / '
                         f'{self.get_last_sequence()}')
            with open(self._cache_filename, 'wb') as f:
                cached = CachedData(self.get_data(), self.get_last_sequence())
                pickle.dump(cached, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.debug(f'Saved.')
            self._last_seq_in_cache = self.get_last_sequence()

    def start(self, mute_events: bool = True, last_seq: int = 0) -> None:
        restored_seq = self.restore_cache()
        # We don't update the sequence here, because remote data source won't know anything about it
        logger.debug(f'Restored from cache, seq: {restored_seq}')

        def redo_log_processed(from_seq: int = 0, last_redo_seq: int = 1) -> None:
            logger.debug(f'Redo log processed, requested seq: {from_seq}, '
                         f'restored seq: {restored_seq}, '
                         f'last redo seq: {last_redo_seq}')
            # Redo log is emptied when the cache is up-to-date AND all strategies from redo log are sent to the server
            if restored_seq > 0:
                super(CachingMixin, self)._emit(events.SourceMessagesProcessed,
                                                {'source': self},
                                                carry='cache')
                from_seq = restored_seq
                logger.debug(f'Emitted SourceMessagesProcessed from cache + redo log')
            logger.debug(f'Starting wrapped source with sequence {from_seq}')
            super(CachingMixin, self).start(mute_events, from_seq)

        self.initialize_redo_log()
        logger.debug('Redo log initialized')

        self._redo_log.on(SourceMessagesProcessed,
                          lambda event, source: redo_log_processed(last_seq, source.get_last_sequence()))
        self._redo_log.start(mute_events, restored_seq)

    def _append(self, strategies: list[AbstractStrategy[TRoot]]) -> None:
        # Question -- what happens with other clients as we replay it? Shall we do it in some "batch" mode,
        # which would mute events on the other side and then "reload the source"? This would be pretty poor in
        # 90% cases, where we couldn't send only one or two strategies. So better just send it as-is.
        if super(CachingMixin, self).is_online():
            logger.debug('Appending strategies to event source')
            super(CachingMixin, self)._append(strategies)
        else:
            logger.debug('Appending strategies to redo log')
            self._redo_log._append(strategies)

    def _send_redo_log(self, **kwargs):
        # Here we know that we've already a). Restored state from cache; b). Replayed redo log;
        logger.debug('Will send redo log')
        super(CachingMixin, self)._append(self._redo_log.read_strategies())
        logger.debug('Redo log sent successfully, will now delete the redo log file')
        os.unlink(self._redo_log_filename)
        self.initialize_redo_log()

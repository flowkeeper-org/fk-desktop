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

import logging
from typing import TypeVar, Generic

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_factory import EventSourceFactory, get_event_source_factory
from fk.core.tenant import Tenant

BeforeSourceChanged = "BeforeSourceChanged"
AfterSourceChanged = "AfterSourceChanged"

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class EventSourceHolder(AbstractEventEmitter, Generic[TRoot]):
    _settings: AbstractSettings
    _cryptograph: AbstractCryptograph
    _source: AbstractEventSource[TRoot] | None

    def __init__(self, settings: AbstractSettings, cryptograph: AbstractCryptograph):
        super().__init__(allowed_events=[BeforeSourceChanged, AfterSourceChanged],
                         callback_invoker=settings.invoke_callback)
        self._settings = settings
        self._cryptograph = cryptograph
        self._source = None

    def request_new_source(self) -> None:
        source_type = self._settings.get('Source.type')
        logger.debug(f'EventSourceHolder: Recreating event source of type {source_type}')
        if not get_event_source_factory().is_valid(source_type):
            # We want to check it earlier, before we unsubscribe the old source
            raise Exception(f"Source type {source_type} not supported")

        self._emit(BeforeSourceChanged, {
            'source': self._source
        })

        # Unsubscribe everyone from the orphan source, so that we don't receive double events
        if self._source is not None:
            self._source.cancel('*')
            self._source.disconnect()

        producer = get_event_source_factory().get_producer(source_type)
        logger.debug(f'EventSourceHolder: About to create new source using producer {producer} with cryptograph {self._cryptograph}')
        self._source = producer(
            self._settings,
            self._cryptograph,
            Tenant(self._settings))
        logger.debug(f'EventSourceHolder: Source object created. You need to start it yourself!')

        self._emit(AfterSourceChanged, {
            'source': self._source
        })

    def get_source(self) -> AbstractEventSource[TRoot] | None:
        return self._source

    def get_settings(self) -> AbstractSettings:
        return self._settings

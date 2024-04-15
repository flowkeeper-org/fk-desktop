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

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_factory import EventSourceFactory
from fk.core.tenant import Tenant

BeforeSourceChanged = "BeforeSourceChanged"
AfterSourceChanged = "AfterSourceChanged"


class EventSourceHolder(AbstractEventEmitter):
    _settings: AbstractSettings
    _source: AbstractEventSource | None

    def __init__(self, settings: AbstractSettings, source: AbstractEventSource | None = None):
        super().__init__(allowed_events=[BeforeSourceChanged, AfterSourceChanged],
                         callback_invoker=settings.invoke_callback)
        self._settings = settings
        self._source = source

    def recreate_source(self) -> None:
        source_type = self._settings.get('Source.type')
        if not EventSourceFactory.get_instance().is_valid(source_type):
            # We want to check it earlier, before we unsubscribe the old source
            raise Exception(f"Source type {source_type} not supported")

        self._emit(BeforeSourceChanged, {
            'source': self._source
        })

        # Unsubscribe everyone from the orphan source, so that we don't receive double events
        if self._source is not None:
            self._source.cancel('*')
            self._source.disconnect()

        self._source = EventSourceFactory.get_instance().get_producer(source_type)(
            self._settings,
            Tenant(self._settings))

        self._emit(AfterSourceChanged, {
            'source': self._source
        })

    def get_source(self) -> AbstractEventSource:
        return self._source

    def get_settings(self) -> AbstractSettings:
        return self._settings

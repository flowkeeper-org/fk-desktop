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
from typing import Self, TypeVar, Iterable

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.simple_serializer import SimpleSerializer

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class EphemeralEventSource(AbstractEventSource[TRoot]):
    _data: TRoot
    _content: list[str]

    def __init__(self,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 root: TRoot):
        super().__init__(SimpleSerializer(settings, cryptograph),
                         settings,
                         cryptograph)
        self._data = root
        self._content = list()

    def start(self, mute_events=True) -> None:
        logger.debug(f'Ephemeral event source -- starting. Muting events -- {mute_events}')
        self._emit(events.SourceMessagesRequested, dict())
        if mute_events:
            self.mute()

        strategy = self.get_init_strategy(self._emit)
        self._content.append(f'{strategy}')
        self.execute_prepared_strategy(strategy)

        if mute_events:
            self.unmute()
        self._emit(events.SourceMessagesProcessed, {'source': self})

    def _append(self, strategies: list[AbstractStrategy[TRoot]]) -> None:
        for s in strategies:
            self._content.append(str(s))

    def get_name(self) -> str:
        return "Ephemeral"

    def get_data(self) -> TRoot:
        return self._data

    def clone(self, new_root: TRoot, existing_strategies: Iterable[AbstractStrategy[TRoot]] | None = None) -> Self:
        return EphemeralEventSource[TRoot](self._settings, self._cryptograph, new_root)

    def disconnect(self):
        self._content.clear()

    def send_ping(self) -> str | None:
        raise Exception("EphemeralEventSource does not support send_ping()")

    def can_connect(self):
        return False

    def dump(self):
        for s in self._content:
            logger.debug(s)

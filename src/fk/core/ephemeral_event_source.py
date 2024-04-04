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
from typing import Self, TypeVar, Iterable

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.strategy_factory import strategy_from_string

TRoot = TypeVar('TRoot')


class EphemeralEventSource(AbstractEventSource[TRoot]):
    _data: TRoot
    _existing_strategies: Iterable[AbstractStrategy] | None
    _last_strategy: AbstractStrategy | None
    _content: list[str]

    def __init__(self,
                 settings: AbstractSettings,
                 root: TRoot,
                 existing_strategies: Iterable[AbstractStrategy] | None = None):
        super().__init__(settings)
        self._data = root
        self._existing_strategies = existing_strategies
        self._last_strategy = None
        self._content = list()

    def get_last_strategy(self) -> AbstractStrategy | None:
        return self._last_strategy

    def start(self, mute_events=True) -> None:
        print('Ephemeral event source -- starting')
        if self._existing_strategies is None:
            self._process_from_file(mute_events)
        else:
            self._process_from_existing()

    def _process_from_existing(self) -> None:
        # This method is called when we repair an existing data source
        # All events are muted during processing
        self._emit(events.SourceMessagesRequested, dict())
        self.mute()
        is_first = True
        seq = 1
        for strategy in self._existing_strategies:
            strategy._data = self._data
            strategy._settings = self._settings
            strategy._emit_func = self._emit
            if type(strategy) is str:
                continue
            self._last_strategy = strategy

            if is_first:
                is_first = False
            else:
                seq = strategy.get_sequence()
                if seq != self._last_seq + 1:
                    self._sequence_error(self._last_seq, seq)
            self._last_seq = seq
            self.execute_prepared_strategy(strategy)
        self.auto_seal()
        self.unmute()
        self._emit(events.SourceMessagesProcessed, dict())

    def _process_from_file(self, mute_events=True) -> None:
        self._emit(events.SourceMessagesRequested, dict())
        if mute_events:
            self.mute()

        s = self.get_data().get_init_strategy(self._emit)
        self._content.append(f'{s}')

        strategy = strategy_from_string(s, self._emit, self.get_data(), self._settings)
        self._last_strategy = strategy
        self._last_seq = strategy.get_sequence()
        self.execute_prepared_strategy(strategy)
        self.auto_seal()

        if mute_events:
            self.unmute()
        self._emit(events.SourceMessagesProcessed, dict())

    def repair(self) -> Iterable[str]:
        return ['Not implemented']

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        for s in strategies:
            self._content.append(str(s))

    def get_name(self) -> str:
        return "Ephemeral"

    def get_data(self) -> TRoot:
        return self._data

    def clone(self, new_root: TRoot, existing_strategies: Iterable[AbstractStrategy] | None = None) -> Self:
        return EphemeralEventSource(self._settings, new_root, existing_strategies)

    def disconnect(self):
        self._content.clear()

    def send_ping(self) -> str | None:
        raise Exception("EphemeralEventSource does not support send_ping()")

    def can_connect(self):
        return False

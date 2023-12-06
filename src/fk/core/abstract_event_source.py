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

import datetime
from abc import ABC, abstractmethod
from typing import Iterable

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.auto_seal import auto_seal
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro
from fk.core.user import User
from fk.core.workitem import Workitem


class AbstractEventSource(AbstractEventEmitter, ABC):

    _settings: AbstractSettings
    _last_seq: int
    _estimated_count: int

    def __init__(self, settings: AbstractSettings):
        AbstractEventEmitter.__init__(self, [
            events.BeforeUserCreate,
            events.AfterUserCreate,
            events.BeforeUserDelete,
            events.AfterUserDelete,
            events.BeforeUserRename,
            events.AfterUserRename,
            events.BeforeBacklogCreate,
            events.AfterBacklogCreate,
            events.BeforeBacklogDelete,
            events.AfterBacklogDelete,
            events.BeforeBacklogRename,
            events.AfterBacklogRename,
            events.BeforeWorkitemCreate,
            events.AfterWorkitemCreate,
            events.BeforeWorkitemComplete,
            events.AfterWorkitemComplete,
            events.BeforeWorkitemStart,
            events.AfterWorkitemStart,
            events.BeforeWorkitemDelete,
            events.AfterWorkitemDelete,
            events.BeforeWorkitemRename,
            events.AfterWorkitemRename,
            events.BeforePomodoroAdd,
            events.AfterPomodoroAdd,
            events.BeforePomodoroRemove,
            events.AfterPomodoroRemove,
            events.BeforePomodoroWorkStart,
            events.AfterPomodoroWorkStart,
            events.BeforePomodoroRestStart,
            events.AfterPomodoroRestStart,
            events.BeforePomodoroComplete,
            events.AfterPomodoroComplete,
            events.SourceMessagesRequested,
            events.SourceMessagesProcessed,
            events.SourceModeReadOnly,
            events.SourceModeReadWrite,
            events.BeforeMessageProcessed,
            events.AfterMessageProcessed,
        ])
        # TODO - Generate client uid for each connection. This will help
        # us do master/slave for strategies.
        self._settings = settings
        self._last_seq = 0
        self._estimated_count = 0

    # Override
    @abstractmethod
    def get_data(self) -> dict[str, User]:
        pass

    # Override
    @abstractmethod
    def get_name(self) -> str:
        pass

    def get_config_parameter(self, name: str) -> str:
        return self._settings.get(name)

    def set_config_parameter(self, name: str, value: str) -> str:
        self._settings.set(name, value)
        return value

    # Assuming those strategies have been already executed. We do not replay them here.
    # Override
    @abstractmethod
    def _append(self, strategies: list[AbstractStrategy]) -> None:
        pass

    # This will initiate connection, which will trigger replay
    @abstractmethod
    def start(self) -> None:
        pass

    def _generate_next_sequence(self) -> int:
        self._last_seq += 1
        return self._last_seq

    def _execute_prepared_strategy(self, strategy: AbstractStrategy) -> None:
        params = {'strategy': strategy}
        self._emit(events.BeforeMessageProcessed, params)
        res = strategy.execute()
        self._emit(events.AfterMessageProcessed, params)
        if res is not None and res[0] == 'auto-seal':
            # A special case for auto-seal. Can be used for other unusual "retry" cases, too.
            self.auto_seal()
            res = strategy.execute()
            if res is not None and res[0] == 'auto-seal':
                raise Exception(f'There is another running pomodoro in "{res[1].get_name()}"')
        self._estimated_count += 1

    def execute(self, strategy_class: type[AbstractStrategy], params: list[str], persist=True):
        # This method is called when the user does something in the UI on THIS instance
        # TODO: Get username from the login provider instead
        now = datetime.datetime.now(datetime.timezone.utc)
        new_sequence = self._last_seq + 1
        s = strategy_class(
            new_sequence,
            now,
            self._settings.get_username(),
            params,
            self._emit,
            self.get_data(),
            self._settings
        )
        self._execute_prepared_strategy(s)

        self._last_seq = new_sequence   # Only save it if all went well
        if persist:
            self._append([s])

    def auto_seal(self) -> None:
        delta = int(self._settings.get('Pomodoro.auto_seal_after'))
        auto_seal(self.workitems(), delta, self.execute)

    def backlogs(self) -> Iterable[Backlog]:
        for user in self.get_data().values():
            for backlog in user.values():
                yield backlog

    def workitems(self) -> Iterable[Workitem]:
        for backlog in self.backlogs():
            for workitem in backlog.values():
                yield workitem

    def pomodoros(self) -> Iterable[Pomodoro]:
        for workitem in self.workitems():
            for pomodoro in workitem.values():
                yield pomodoro

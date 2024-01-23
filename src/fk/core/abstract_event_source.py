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
from os import path
from typing import Iterable, Self, Callable, TypeVar, Generic

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.auto_seal import auto_seal
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro
from fk.core.strategy_factory import strategy_from_string
from fk.core.user_strategies import CreateUserStrategy
from fk.core.workitem import Workitem

TRoot = TypeVar('TRoot')


class AbstractEventSource(AbstractEventEmitter, ABC, Generic[TRoot]):

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
            events.PongReceived,
        ], settings.invoke_callback)
        # TODO - Generate client uid for each connection. This will help
        # us do master/slave for strategies.
        self._settings = settings
        self._last_seq = 0
        self._estimated_count = 0

    # Override
    @abstractmethod
    def get_data(self) -> TRoot:
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
    def start(self, mute_events=True) -> None:
        pass

    def _execute_prepared_strategy(self, strategy: AbstractStrategy, auto: bool = False) -> None:
        params = {'strategy': strategy, 'auto': auto}
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

    def execute(self,
                strategy_class:
                type[AbstractStrategy],
                params: list[str],
                persist: bool = True,
                auto: bool = False,
                carry: any = None) -> None:
        # This method is called when the user does something in the UI on THIS instance
        # TODO: Get username from the login provider instead
        now = datetime.datetime.now(datetime.timezone.utc)
        new_sequence = self._last_seq + 1
        s = strategy_class(
            new_sequence,
            now,
            self.get_data().get_user(self._settings.get_username()),
            params,
            self._emit,
            self.get_data(),
            self._settings,
            carry
        )
        self._execute_prepared_strategy(s, auto)

        if persist:
            self._last_seq = new_sequence   # Only save it if all went well
            self._append([s])

    def auto_seal(self) -> None:
        delta = int(self._settings.get('Pomodoro.auto_seal_after'))
        auto_seal(self.workitems(),
                  delta,
                  lambda strategy_class, params, persist: self.execute(strategy_class,
                                                                       params,
                                                                       persist,
                                                                       auto=True))

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

    @abstractmethod
    def clone(self, new_root: TRoot) -> Self:
        pass

    def _export_message_processed(self,
                                  another: Self,
                                  export_file,
                                  progress_callback: Callable[[int, int], None],
                                  every: int,
                                  strategy: AbstractStrategy) -> None:
        export_file.write(f'{strategy}\n')
        if another._estimated_count % every == 0:
            progress_callback(another._estimated_count, self._estimated_count)
            # print(f' - {another._estimated_count} out of {self._estimated_count}')

    @staticmethod
    def _export_completed(another: Self,
                          export_file,
                          completion_callback: Callable[[int], None]) -> None:
        export_file.close()
        completion_callback(another._estimated_count)

    def export(self,
               filename: str,
               new_root: Self,
               start_callback: Callable[[int], None],
               progress_callback: Callable[[int, int], None],
               completion_callback: Callable[[int], None]) -> None:
        another = self.clone(new_root)
        every = max(int(self._estimated_count / 100), 1)
        export_file = open(filename, 'w', encoding='UTF-8')
        another.on(events.AfterMessageProcessed,
                   lambda event, strategy, auto: self._export_message_processed(another,
                                                                                     export_file,
                                                                                     progress_callback,
                                                                                     every,
                                                                                     strategy) if not auto else None)
        another.on(events.SourceMessagesProcessed,
                   lambda event: AbstractEventSource._export_completed(another,
                                                                            export_file,
                                                                            completion_callback))
        start_callback(self._estimated_count)
        another.start(mute_events=False)

    def import_(self,
                filename: str,
                ignore_errors: bool,
                start_callback: Callable[[int], None],
                progress_callback: Callable[[int, int], None],
                completion_callback: Callable[[int], None]) -> None:
        # Note that this method ignores sequences and will import even "broken" files
        if not path.isfile(filename):
            raise Exception(f'File {filename} not found')

        with open(filename, 'rb') as f:
            total = sum(1 for _ in f)
            every = max(int(total / 100), 1)

        start_callback(total)
        self.mute()

        i = 0
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                try:
                    strategy = strategy_from_string(line,
                                                    self._emit,
                                                    self.get_data(),
                                                    self._settings,
                                                    list(self.get_data().values())[0])
                    i += 1
                    if type(strategy) is str:
                        continue
                    if type(strategy) is CreateUserStrategy:
                        continue
                    self.execute(type(strategy), strategy.get_params())
                    if i % every == 0:
                        progress_callback(i, total)
                except Exception as e:
                    if ignore_errors:
                        print('Warning', e)
                    else:
                        raise e

        self.unmute()
        completion_callback(total)

    def _sequence_error(self, prev: int, next: int) -> None:
        raise Exception(f"Strategies must go in sequence. "
                        f"Received {next} after {prev}. "
                        f"To attempt a repair go to Settings > Connection > Repair.")

    @abstractmethod
    def disconnect(self):
        pass

    def get_settings(self) -> AbstractSettings:
        return self._settings

    @abstractmethod
    def send_ping(self) -> str | None:
        pass

    @abstractmethod
    def can_connect(self):
        pass

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
import logging
from abc import ABC, abstractmethod
from os import path
from typing import Iterable, Self, Callable, TypeVar, Generic

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.auto_seal import auto_seal
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import AddPomodoroStrategy, VoidPomodoroStrategy, StartWorkStrategy, StartRestStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tenant import ADMIN_USER
from fk.core.user import User
from fk.core.user_strategies import CreateUserStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, CompleteWorkitemStrategy

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class AbstractEventSource(AbstractEventEmitter, ABC, Generic[TRoot]):

    _serializer: AbstractSerializer
    _settings: AbstractSettings
    _cryptograph: AbstractCryptograph
    _last_seq: int
    _estimated_count: int

    def __init__(self,
                 serializer: AbstractSerializer,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph):
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
            events.BeforeMessageProcessed,
            events.AfterMessageProcessed,
            events.PongReceived,
        ], settings.invoke_callback)
        # TODO - Generate client uid for each connection. This will help us do master/slave for strategies.
        self._serializer = serializer
        self._settings = settings
        self._cryptograph = cryptograph
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

    def set_config_parameters(self, values: dict[str, str]) -> None:
        self._settings.set(values)

    # Assuming those strategies have been already executed. We do not replay them here.
    # Override
    @abstractmethod
    def _append(self, strategies: list[AbstractStrategy[TRoot]]) -> None:
        pass

    # This will initiate connection, which will trigger replay
    @abstractmethod
    def start(self, mute_events=True) -> None:
        pass

    def execute_prepared_strategy(self, strategy: AbstractStrategy[TRoot], auto: bool = False) -> None:
        params = {'strategy': strategy, 'auto': auto}
        self._emit(events.BeforeMessageProcessed, params)
        res = strategy.execute(self._emit, self.get_data())
        self._emit(events.AfterMessageProcessed, params)
        if res is not None and res[0] == 'auto-seal':
            # A special case for auto-seal. Can be used for other unusual "retry" cases, too.
            self.auto_seal()
            res = strategy.execute(self._emit, self.get_data())
            if res is not None and res[0] == 'auto-seal':
                raise Exception(f'There is another running pomodoro in "{res[1].get_name()}"')
        self._estimated_count += 1

    def execute(self,
                strategy_class: type[AbstractStrategy[TRoot]],
                params: list[str],
                persist: bool = True,
                when: datetime.datetime = None,
                auto: bool = False,
                carry: any = None) -> None:
        # This method is called when the user does something in the UI on THIS instance
        # TODO: Get username from the login provider instead
        if when is None:
            when = datetime.datetime.now(datetime.timezone.utc)
        new_sequence = self._last_seq + 1
        s = strategy_class(
            new_sequence,
            when,
            self._settings.get_username(),
            params,
            self._settings,
            carry)
        self.execute_prepared_strategy(s, auto)

        if persist:
            self._last_seq = new_sequence   # Only save it if all went well
            self._append([s])

    def auto_seal(self) -> None:
        delta = float(self._settings.get('Pomodoro.auto_seal_after'))
        auto_seal(self.workitems(),
                  delta,
                  lambda strategy_class, params, persist, when: self.execute(strategy_class,
                                                                             params,
                                                                             persist=persist,
                                                                             when=when,
                                                                             auto=True))

    def users(self) -> Iterable[User]:
        for user in self.get_data().values():
            yield user

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
                                  strategy: AbstractStrategy[TRoot],
                                  export_serializer: AbstractSerializer) -> None:
        serialized = export_serializer.serialize(strategy)
        export_file.write(f'{serialized}\n')
        if another._estimated_count % every == 0:
            progress_callback(another._estimated_count, self._estimated_count)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f' - {another._estimated_count} out of {self._estimated_count}')

    def _export_completed(self,
                          another: Self,
                          export_file,
                          completion_callback: Callable[[int], None]) -> None:
        export_file.close()
        completion_callback(another._estimated_count)

    def strategies(self) -> Iterable[AbstractStrategy]:
        seq = 1
        for user in self.get_data().values():
            if user.is_system_user():
                continue
            yield CreateUserStrategy(seq, user.get_create_date(), ADMIN_USER,
                                     [user.get_identity(), user.get_name()],
                                     self._settings)
            seq += 1
            for backlog in user.values():
                yield CreateBacklogStrategy(seq, backlog.get_create_date(), user.get_identity(),
                                            [backlog.get_uid(), backlog.get_name()],
                                            self._settings)
                seq += 1
                for workitem in backlog.values():
                    yield CreateWorkitemStrategy(seq, workitem.get_create_date(), user.get_identity(),
                                                 [workitem.get_uid(), backlog.get_uid(), workitem.get_name()],
                                                 self._settings)
                    seq += 1
                    for pomodoro in workitem.values():
                        # We could create all at once, but then we'd lose the information about unplanned pomodoros
                        yield AddPomodoroStrategy(seq, workitem.get_create_date(), user.get_identity(),
                                                  [workitem.get_uid(), '1'],
                                                  self._settings)
                        seq += 1
                        if pomodoro.is_canceled() or pomodoro.is_finished():
                            yield StartWorkStrategy(seq,
                                                    pomodoro.get_last_modified_date() - datetime.timedelta(seconds=1),
                                                    user.get_identity(),
                                                    [workitem.get_uid(), '1'],
                                                    self._settings)
                            seq += 1
                        if pomodoro.is_canceled():
                            yield VoidPomodoroStrategy(seq, pomodoro.get_last_modified_date(), user.get_identity(),
                                                       [workitem.get_uid()],
                                                       self._settings)
                            seq += 1
                        elif pomodoro.is_finished():
                            yield StartRestStrategy(seq, pomodoro.get_last_modified_date(), user.get_identity(),
                                                    [workitem.get_uid(), '1'],
                                                    self._settings)
                            seq += 1
                    if workitem.is_sealed():
                        yield CompleteWorkitemStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                       [workitem.get_uid(), 'finished'],
                                                       self._settings)
                        seq += 1

    def _export_compressed(self,
                           another: Self,
                           export_file,
                           completion_callback: Callable[[int], None],
                           export_serializer: AbstractSerializer) -> None:
        # Convert Flowkeeper data structure into a list of strategies
        for strategy in self.strategies():
            serialized = export_serializer.serialize(strategy)
            export_file.write(f'{serialized}\n')
        self._export_completed(another, export_file, completion_callback)

    def export(self,
               filename: str,
               new_root: TRoot,
               encrypt: bool,
               compress: bool,
               start_callback: Callable[[int], None],
               progress_callback: Callable[[int, int], None],
               completion_callback: Callable[[int], None]) -> None:
        export_serializer = self.create_export_serializer(encrypt)
        another = self.clone(new_root)
        every = max(int(self._estimated_count / 100), 1)
        export_file = open(filename, 'w', encoding='UTF-8')

        if compress:
            another.on(events.SourceMessagesProcessed,
                       lambda **kwargs: self._export_compressed(another,
                                                                export_file,
                                                                completion_callback,
                                                                export_serializer))
        else:
            another.on(events.AfterMessageProcessed,
                       lambda strategy, auto, **kwargs: None if auto else self._export_message_processed(another,
                                                                                                         export_file,
                                                                                                         progress_callback,
                                                                                                         every,
                                                                                                         strategy,
                                                                                                         export_serializer))
            another.on(events.SourceMessagesProcessed,
                       lambda **kwargs: self._export_completed(another,
                                                               export_file,
                                                               completion_callback))

        start_callback(self._estimated_count)
        another.start(mute_events=False)

    def create_export_serializer(self, encrypt=False) -> AbstractSerializer:
        if encrypt:
            return SimpleSerializer(self._settings, self._cryptograph)
        else:
            return SimpleSerializer(self._settings, NoCryptograph(self._settings))

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

        user_identity = self._settings.get_username()

        # With encrypt=True it will try to deserialize as much as possible
        export_serializer = self.create_export_serializer(True)

        i = 0
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                try:
                    strategy = export_serializer.deserialize(line)
                    strategy.replace_user_identity(user_identity)
                    i += 1
                    if strategy is None:
                        continue
                    if type(strategy) is CreateUserStrategy:
                        continue
                    self.execute(type(strategy), strategy.get_params())
                    if i % every == 0:
                        progress_callback(i, total)
                except Exception as e:
                    if ignore_errors:
                        logger.warning('Ignored an error while importing', exc_info=e)
                    else:
                        raise e

        self.unmute()
        completion_callback(total)

    def _sequence_error(self, prev: int, next_: int) -> None:
        raise Exception(f"Strategies must go in sequence. "
                        f"Received {next_} after {prev}. "
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

    def get_init_strategy(self, emit: Callable[[str, dict[str, any], any], None]) -> AbstractStrategy[Self]:
        return CreateUserStrategy(1,
                                  datetime.datetime.now(datetime.timezone.utc),
                                  ADMIN_USER,
                                  [self._settings.get_username(), self._settings.get_fullname()],
                                  self._settings)

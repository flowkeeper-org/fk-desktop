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

import datetime
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Iterable, Callable, TypeVar, Generic

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_TRACKER
from fk.core.pomodoro_strategies import AddPomodoroStrategy
from fk.core.tag import Tag
from fk.core.tenant import ADMIN_USER, Tenant
from fk.core.timer_data import TimerData
from fk.core.timer_strategies import TimerRingInternalStrategy, StartTimerStrategy
from fk.core.user import User
from fk.core.user_strategies import CreateUserStrategy, AutoSealInternalStrategy
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot', bound=Tenant)


class AbstractEventSource(AbstractEventEmitter, ABC, Generic[TRoot]):

    _serializer: AbstractSerializer
    _settings: AbstractSettings
    _cryptograph: AbstractCryptograph
    _last_seq: int
    _estimated_count: int
    _ignore_invalid_sequences: bool
    _ignore_errors: bool
    _online: bool

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
            events.BeforeBacklogReorder,
            events.AfterBacklogReorder,
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
            events.BeforeWorkitemReorder,
            events.AfterWorkitemReorder,
            events.BeforeWorkitemMove,
            events.AfterWorkitemMove,
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
            events.BeforePomodoroVoided,
            events.AfterPomodoroVoided,
            events.BeforePomodoroInterrupted,
            events.AfterPomodoroInterrupted,
            events.TagCreated,
            events.TagDeleted,
            events.TagContentChanged,
            events.SourceMessagesRequested,
            events.SourceMessagesProcessed,
            events.BeforeMessageProcessed,
            events.AfterMessageProcessed,
            events.PongReceived,
            events.TimerWorkStart,
            events.TimerRestComplete,
            events.TimerWorkComplete,
            events.WentOnline,
            events.WentOffline,
        ], settings.invoke_callback)
        # TODO - Generate client uid for each connection. This will help us do master/slave for strategies.
        self._serializer = serializer
        self._settings = settings
        self._cryptograph = cryptograph
        self._last_seq = 0
        self._estimated_count = 0
        self._online = False
        self._ignore_invalid_sequences = settings.get('Source.ignore_invalid_sequence') == 'True'
        self._ignore_errors = settings.get('Source.ignore_errors') == 'True'

    # TODO: Create ConnectedEventSource and move it there
    def went_online(self, ping: int = 0) -> None:
        if not self._online:
            logger.debug(f'Went online')
            self._emit(events.WentOnline, {
                'ping': ping,
            }, force=True)
        self._online = True

    def went_offline(self, after: int = 0, last_received: datetime.datetime = None) -> None:
        if self._online:
            logger.debug('Went offline')
            self._emit(events.WentOffline, {
                'after': after,
                'last_received': last_received,
            }, force=True)  # We always fire connection state events
        self._online = False

    def is_online(self) -> bool:
        return self._online

    # Override
    @abstractmethod
    def get_data(self) -> TRoot:
        pass

    @abstractmethod
    def set_data(self, data: TRoot) -> None:
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
    def append(self, strategies: Iterable[AbstractStrategy[TRoot]]) -> None:
        pass

    # This will initiate connection, which will trigger replay
    @abstractmethod
    def start(self, mute_events: bool = True, last_seq: int = 0) -> None:
        pass

    def _auto_seal_at_the_end(self, last_executed: AbstractStrategy) -> None:
        if last_executed is not None:
            sealant = AutoSealInternalStrategy(last_executed.get_sequence(),
                                               datetime.datetime.now(datetime.timezone.utc),
                                               last_executed.get_user_identity(),
                                               [],
                                               self.get_settings(),
                                               None)
            self.execute_prepared_strategy(sealant, True, False)

    def _auto_seal(self, strategy: AbstractStrategy[TRoot], second_time: bool = False):
        timer: TimerData = strategy.get_user(self.get_data()).get_timer()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'Auto-sealing, timer: {timer}, second time: {second_time}')
        if second_time:
            pass
        if timer.is_ticking():
            expected_timer_ring = timer.get_next_state_change()
            if expected_timer_ring is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Expected to ring at {expected_timer_ring}, comparing to {strategy.get_when()}')
                # Adding one-second margin to account for the series mode, where the next pomodoro starts automatically
                # on timer immediately after the previous one finishes. In this case we depend on the timers accuracy,
                # which in practice results in ~0.3s errors back and forth. Sometimes this results in the "Can't start
                # next pomodoro because the timer is still ticking" errors when loading strategies.
                if strategy.get_when() + timedelta(seconds=1) >= expected_timer_ring:
                    # Timer rings, maybe even twice
                    strategy.execute_another(self._emit,
                                             self.get_data(),
                                             TimerRingInternalStrategy,
                                             [],
                                             expected_timer_ring)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Rang the timer, resulting state: {timer}')
                    if timer.is_ticking():
                        if second_time:
                            logger.error(f'The timer is still ticking after stopping it twice. Strategy: {strategy}')
                            raise Exception("The timer refuses to ring. "
                                            "This should never happen, please report it as a bug.")
                        self._auto_seal(strategy, True)

    def execute_prepared_strategy(self,
                                  strategy: AbstractStrategy[TRoot],
                                  auto: bool = False,
                                  persist: bool = False) -> None:
        if strategy.requires_sealing():
            self._auto_seal(strategy)

        params = {
            'strategy': strategy,
            'auto': auto,
            'persist': persist,
        }
        # UC-2: All executed strategies are wrapped in BeforeMessageProcessed / AfterMessageProcessed events.
        self._emit(events.BeforeMessageProcessed, params)

        try:
            strategy.execute(self._emit, self.get_data())
            self._estimated_count += 1
            if persist:
                self._append([strategy])
                # UC-2: Strategy sequence is incremented only after it is persisted
                self._last_seq = strategy.get_sequence()   # Only save it if all went well
        finally:
            # UC-2: AfterMessageProcessed is triggered after the strategy is persisted, no matter what
            self._emit(events.AfterMessageProcessed, params)

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
        s = strategy_class(
            self._last_seq + 1,
            when,
            self._settings.get_username(),  # UC-2: Strategy owner is taken from the source settings
            params,
            self._settings,
            carry)
        self.execute_prepared_strategy(s, auto, persist)

    def users(self) -> Iterable[User]:
        for user in self.get_data().values():
            yield user

    def backlogs(self) -> Iterable[Backlog]:
        for user in self.get_data().values():
            for backlog in user.values():
                yield backlog

    def tags(self) -> Iterable[Tag]:
        for user in self.get_data().values():
            for tag in user.get_tags().values():
                yield tag

    def workitems(self) -> Iterable[Workitem]:
        for backlog in self.backlogs():
            for workitem in backlog.values():
                yield workitem

    def pomodoros(self) -> Iterable[Pomodoro]:
        for workitem in self.workitems():
            for pomodoro in workitem.values():
                yield pomodoro

    def find_workitem(self, uid: str) -> Workitem | None:
        for workitem in self.workitems():
            if workitem.get_uid() == uid:
                return workitem

    def find_backlog(self, uid: str) -> Backlog | None:
        for backlog in self.backlogs():
            if backlog.get_uid() == uid:
                return backlog

    def find_tag(self, uid: str) -> Tag | None:
        for tag in self.tags():
            if tag.get_uid() == uid:
                return tag

    def find_user(self, identity: str) -> User | None:
        for user in self.users():
            if user.get_identity() == identity:
                return user

    @abstractmethod
    def clone(self, new_root: TRoot) -> AbstractEventSource[TRoot]:
        pass

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

    @abstractmethod
    def repair(self) -> tuple[list[str], str | None]:
        pass

    def connect(self):
        raise Exception('Connect is not supported on this type of event source')

    def get_init_strategy(self, emit: Callable[[str, dict[str, any], any], None]) -> AbstractStrategy[TRoot]:
        return CreateUserStrategy(1,
                                  datetime.datetime.now(datetime.timezone.utc),
                                  ADMIN_USER,
                                  [self._settings.get_username(), self._settings.get_fullname()],
                                  self._settings)

    def get_last_sequence(self):
        return self._last_seq

    @abstractmethod
    def get_id(self) -> str:
        pass


# ********************* Misc. Utils *********************


def start_workitem(workitem: Workitem, source: AbstractEventSource) -> None:
    settings = source.get_settings()

    # TODO: Move this entire piece of logic into StartTimerStrategy
    if len(workitem) == 0 or workitem.is_tracker():
        # This is going to be a tracker workitem
        source.execute(AddPomodoroStrategy, [
            workitem.get_uid(),
            "1",
            POMODORO_TYPE_TRACKER
        ])
        source.execute(StartTimerStrategy, [
            workitem.get_uid(),
        ])
    else:
        rest_duration = None

        if settings.get('Pomodoro.long_break_algorithm') == 'simple':
            timer: TimerData = source.get_data().get_current_user().get_timer()
            pomodoro_in_series = timer.get_pomodoro_in_series()
            if pomodoro_in_series >= int(settings.get('Pomodoro.long_break_each')) - 1:
                logger.debug('The user starts a workitem. A long break is suggested after it is completed.')
                rest_duration = "0"

        if rest_duration is None:  # Default to standard duration
            logger.debug('The user starts a workitem. A short break is suggested after it is completed.')
            rest_duration = settings.get('Pomodoro.default_rest_duration')

        source.execute(StartTimerStrategy, [
            workitem.get_uid(),
            settings.get('Pomodoro.default_work_duration'),
            rest_duration,
        ])

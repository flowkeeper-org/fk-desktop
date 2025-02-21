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

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer import AbstractTimer
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER
from fk.core.timer_data import TimerData
from fk.core.timer_strategies import TimerRingInternalStrategy

logger = logging.getLogger(__name__)


class PomodoroTimer(AbstractEventEmitter):
    _tick_timer: AbstractTimer
    _transition_timer: AbstractTimer
    _source_holder: EventSourceHolder

    @property
    def timer(self) -> TimerData:
        return self._source_holder.get_source().get_data().get_current_user().get_timer()

    # Emitted events
    TimerTick = "TimerTick"

    def __init__(self,
                 tick_timer: AbstractTimer,
                 transition_timer: AbstractTimer,
                 settings: AbstractSettings,
                 source_holder: EventSourceHolder):
        super().__init__([self.TimerTick],
                         settings.invoke_callback)
        logger.debug('PomodoroTimer: Initializing')
        self._tick_timer = tick_timer
        self._transition_timer = transition_timer
        self._source_holder = source_holder
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        logger.debug('PomodoroTimer: Initialized')

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        source.on(events.SourceMessagesProcessed, self._refresh)
        source.on(events.AfterPomodoroWorkStart, self._handle_pomodoro_work_start)
        source.on(events.AfterPomodoroRestStart, self._handle_pomodoro_rest_start)
        source.on(events.AfterPomodoroComplete, self._handle_pomodoro_complete)
        source.on(events.AfterPomodoroVoided, self._handle_pomodoro_complete)

    def _refresh(self, event: str | None = None, when: datetime.datetime | None = None, **kwargs) -> None:
        logger.debug('PomodoroTimer: Refreshing')
        timer = self.timer
        pomodoro: Pomodoro | None = timer.get_running_pomodoro()

        if pomodoro is None:
            logger.debug('PomodoroTimer: Currently idle')
            self._transition_timer.cancel()
            self._tick_timer.cancel()
        elif pomodoro is not None:
            self._transition_timer.cancel()
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL and timer.get_remaining_duration() > 0:
                self._schedule_tick()
                if pomodoro.is_working():
                    logger.debug(f'PomodoroTimer: Is working')
                    self._schedule_transition(
                        timer.get_remaining_duration() * 1000,
                        pomodoro,
                        'rest')
                elif pomodoro.is_resting():
                    logger.debug(f'PomodoroTimer: Is resting')
                    self._schedule_transition(
                        timer.get_remaining_duration() * 1000,
                        pomodoro,
                        'finished')
                else:
                    raise Exception(f'Unexpected running state: {pomodoro.get_state()}')
            elif pomodoro.get_type() == POMODORO_TYPE_TRACKER:
                self._schedule_tick()

    def _schedule_tick(self) -> None:
        self._tick_timer.schedule(990, self._handle_tick, None)

    def _handle_tick(self, params: dict | None, when: datetime.datetime | None = None) -> None:
        timer = self.timer
        if timer.is_ticking():
            self._emit(PomodoroTimer.TimerTick, {
                'timer': timer,
            }, None)

    def _schedule_transition(self,
                             ms: float,
                             target_pomodoro: Pomodoro,
                             target_state: str) -> None:
        logger.debug(f'PomodoroTimer: Scheduled transition to {target_state} in {ms / 1000} seconds')
        self._transition_timer.schedule(ms, self._handle_transition, {
            'target_pomodoro': target_pomodoro,
            'target_state': target_state,
        }, True)
        logger.debug(f'PomodoroTimer: Done - Scheduled transition to {target_state} in {ms / 1000} seconds')

    def _handle_transition(self, params: dict | None, when: datetime.datetime | None) -> None:
        timer = self.timer
        target_pomodoro: Pomodoro = params['target_pomodoro']
        target_state: str = params['target_state']
        logger.debug(f'PomodoroTimer: Handling transition from {timer.get_state()} to {target_state}')
        if target_pomodoro.is_finished():
            logger.debug(f"We've already sealed this pomodoro, nothing else to do")
            return
        if target_state == 'rest' or target_state == 'finished':
            # Getting fresh rest duration in case it changed since the pomodoro was created.
            # Note that we get the fresh work duration as soon as the work starts (see get_work_duration()).
            logger.debug(f"Will execute TimerRingInternalStrategy()")
            self._source_holder.get_source().execute(
                TimerRingInternalStrategy,
                [],
                persist=False,
                when=when)
            logger.debug(f"PomodoroTimer: Executed TimerRingInternalStrategy")
        elif target_state == 'new':
            logger.debug(f"PomodoroTimer: Pomodoro is voided, nothing else to do")
        else:
            raise Exception(f"Unexpected scheduled transition state: {target_state}")
        logger.debug(f'PomodoroTimer: Done - Handling transition to {target_state}')

    def _handle_pomodoro_work_start(self,
                                    pomodoro: Pomodoro,
                                    work_duration: float,
                                    **kwargs) -> None:
        logger.debug(f'Handling work start')
        if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
            self._schedule_transition(work_duration * 1000, pomodoro, 'rest')
        self._schedule_tick()
        logger.debug(f'PomodoroTimer: Done - Handling work start')

    def _handle_pomodoro_rest_start(self,
                                    pomodoro: Pomodoro,
                                    rest_duration: float,
                                    **kwargs) -> None:
        logger.debug(f'PomodoroTimer: Handling rest start')
        self._schedule_transition(rest_duration * 1000, pomodoro, 'finished')
        logger.debug(f'PomodoroTimer: Done - Handling rest start')

    def _handle_pomodoro_complete(self,
                                  pomodoro: Pomodoro,
                                  **kwargs) -> None:
        logger.debug(f'PomodoroTimer: Handling pomodoro complete or void')
        # It might look better to just check for the terminal conditions directly in the handlers instead
        # of canceling timers here. We are going the latter path to account for scenarios when stuff gets
        # void because of cascading deletes. For instance, if we delete a Workitem with a running pomodoro,
        # the latter is canceled automatically. If we were to check this in the handler, we would've been
        # ticking and running stuff against zombie objects, which might be dangerous form the data
        # consistency point of view.
        self._transition_timer.cancel()
        self._tick_timer.cancel()
        logger.debug('PomodoroTimer: Canceled transition timer')
        logger.debug(f'PomodoroTimer: Done - Handling pomodoro complete or void')

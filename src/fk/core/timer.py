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
from datetime import timedelta

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer import AbstractTimer
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER
from fk.core.timer_strategies import StartRestInternalStrategy, FinishPomodoroInternalStrategy
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)


# This timer never goes below 0
class PomodoroTimer(AbstractEventEmitter):
    _tick_timer: AbstractTimer
    _transition_timer: AbstractTimer
    _state: str | None
    _pomodoro: Pomodoro | None
    _workitem: Workitem | None
    _planned_duration: float
    _remaining_duration: float
    _source_holder: EventSourceHolder

    # Emitted events
    TimerTick = "TimerTick"
    TimerWorkStart = "TimerWorkStart"
    TimerWorkComplete = "TimerWorkComplete"
    TimerRestComplete = "TimerRestComplete"
    TimerInitialized = "TimerInitialized"

    def __init__(self,
                 tick_timer: AbstractTimer,
                 transition_timer: AbstractTimer,
                 settings: AbstractSettings,
                 source_holder: EventSourceHolder):
        super().__init__([self.TimerTick,
                          self.TimerWorkStart,
                          self.TimerWorkComplete,
                          self.TimerRestComplete,
                          self.TimerInitialized,
                          ],
                         settings.invoke_callback)
        logger.debug('PomodoroTimer: Initializing')
        self._tick_timer = tick_timer
        self._transition_timer = transition_timer
        self._source_holder = source_holder
        self._reset()
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        logger.debug('PomodoroTimer: Initialized')

    def _reset(self):
        self._state = None
        self._pomodoro = None
        self._workitem = None
        self._planned_duration = 0
        self._remaining_duration = 0

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._reset()
        source.on(events.SourceMessagesProcessed, self._refresh)
        source.on(events.AfterPomodoroWorkStart, self._handle_pomodoro_work_start)
        source.on(events.AfterPomodoroRestStart, self._handle_pomodoro_rest_start)
        source.on(events.AfterPomodoroComplete, self._handle_pomodoro_complete)
        source.on(events.AfterPomodoroVoided, self._handle_pomodoro_complete)

    def _refresh(self, event: str | None = None, when: datetime.datetime | None = None, **kwargs) -> None:
        logger.debug('PomodoroTimer: Refreshing')
        workitem: Workitem | None = None
        pomodoro: Pomodoro | None = None
        for backlog in self._source_holder.get_source().backlogs():
            w, p = backlog.get_running_workitem()
            if w is not None:
                workitem = w
                pomodoro = p
                break

        if workitem is None:
            logger.debug('PomodoroTimer: Currently idle')
            self._state = 'idle'    # work, rest, idle
            self._pomodoro = None
            self._workitem = None
            self._planned_duration = 0
            self._remaining_duration = 0
            self._transition_timer.cancel()
            self._tick_timer.cancel()
        elif workitem is not None and pomodoro is not None:
            self._state = 'rest' if pomodoro.get_type() == POMODORO_TYPE_NORMAL and pomodoro.is_resting() else 'work'
            logger.debug(f'PomodoroTimer: Current state is "{self._state}"')
            self._pomodoro = pomodoro
            self._workitem = workitem
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                self._planned_duration = pomodoro.get_rest_duration() \
                    if pomodoro.is_resting() else pomodoro.get_work_duration()
                self._remaining_duration = max(pomodoro.remaining_time_in_current_state(when), 0)
            else:
                self._planned_duration = None
                self._remaining_duration = None
            self._transition_timer.cancel()
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL and self._remaining_duration > 0:
                self._schedule_tick()
                if pomodoro.is_working():
                    logger.debug(f'PomodoroTimer: Is working')
                    self._schedule_transition(
                        self._remaining_duration * 1000,
                        pomodoro,
                        workitem,
                        'rest')
                elif pomodoro.is_resting():
                    logger.debug(f'PomodoroTimer: Is resting')
                    self._schedule_transition(
                        self._remaining_duration * 1000,
                        pomodoro,
                        workitem,
                        'finished')
                else:
                    raise Exception(f'Unexpected running state: {pomodoro.get_state()}')
            elif pomodoro.get_type() == POMODORO_TYPE_TRACKER:
                self._schedule_tick()

        self._emit(PomodoroTimer.TimerInitialized, {
            'timer': self,
        }, None)

    def __str__(self):
        return f'Timer is {self._state}'

    def _schedule_tick(self) -> None:
        self._tick_timer.schedule(990, self._handle_tick, None)

    def _handle_tick(self, params: dict | None, when: datetime.datetime | None = None) -> None:
        if self._pomodoro is not None:
            if self._pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                self._remaining_duration = max(self._pomodoro.remaining_time_in_current_state(when), 0)
            # Only tick if there's something running
            self._emit(PomodoroTimer.TimerTick, {
                'timer': self,
                'pomodoro': self._pomodoro,
            }, None)

    def _schedule_transition(self,
                             ms: float,
                             target_pomodoro: Pomodoro,
                             target_workitem: Workitem,
                             target_state: str) -> None:
        logger.debug(f'PomodoroTimer: Scheduled transition to {target_state} in {ms / 1000} seconds')
        self._transition_timer.schedule(ms, self._handle_transition, {
            'target_pomodoro': target_pomodoro,
            'target_workitem': target_workitem,
            'target_state': target_state,
        }, True)
        logger.debug(f'PomodoroTimer: Done - Scheduled transition to {target_state} in {ms / 1000} seconds')

    def _handle_transition(self, params: dict | None, when: datetime.datetime | None) -> None:
        target_pomodoro: Pomodoro = params['target_pomodoro']
        target_workitem: Workitem = params['target_workitem']
        target_state: str = params['target_state']
        logger.debug(f'PomodoroTimer: Handling transition from {self._state} to {target_state}')
        if target_pomodoro.is_finished():
            logger.debug(f"We've already sealed this pomodoro, nothing else to do")
            return
        if target_state == 'rest':
            # Getting fresh rest duration in case it changed since the pomodoro was created.
            # Note that we get the fresh work duration as soon as the work starts (see get_work_duration()).
            logger.debug(f"Will execute StartRestInternalStrategy('{target_workitem.get_name()}')")
            self._source_holder.get_source().execute(
                StartRestInternalStrategy,
                [target_workitem.get_uid()],
                persist=False,
                when=when)
            logger.debug(f"PomodoroTimer: Executed StartRestInternalStrategy")
        elif target_state == 'finished':
            logger.debug(f"PomodoroTimer: Will execute FinishPomodoroInternalStrategy('{target_workitem.get_name()}', 'finished')")
            self._source_holder.get_source().execute(
                FinishPomodoroInternalStrategy,
                [target_workitem.get_uid()],
                persist=False,
                when=when)
            logger.debug(f"PomodoroTimer: Executed FinishPomodoroInternalStrategy")
        elif target_state == 'new':
            logger.debug(f"PomodoroTimer: Pomodoro is voided, nothing else to do")
        else:
            raise Exception(f"Unexpected scheduled transition state: {target_state}")
        logger.debug(f'PomodoroTimer: Done - Handling transition to {target_state}')

    def _handle_pomodoro_work_start(self,
                                    event: str,
                                    pomodoro: Pomodoro,
                                    workitem: Workitem,
                                    work_duration: float,
                                    **kwargs) -> None:
        logger.debug(f'Handling work start')
        self._pomodoro = pomodoro
        self._workitem = workitem
        self._state = 'work'
        self._planned_duration = work_duration
        self._remaining_duration = work_duration
        self._emit(PomodoroTimer.TimerWorkStart, {
            'timer': self,
        })
        if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
            self._schedule_transition(work_duration * 1000, pomodoro, workitem, 'rest')
        self._schedule_tick()
        logger.debug(f'PomodoroTimer: Done - Handling work start')

    def _handle_pomodoro_rest_start(self,
                                    event: str,
                                    pomodoro: Pomodoro,
                                    workitem: Workitem,
                                    rest_duration: float,
                                    **kwargs) -> None:
        logger.debug(f'PomodoroTimer: Handling rest start')
        if pomodoro != self._pomodoro:
            logger.warning("PomodoroTimer: Warning - Timer detected start of an unexpected pomodoro")
        if workitem != self._workitem:
            logger.warning(f"PomodoroTimer: Warning - Timer detected start of an unexpected workitem ({workitem} != {self._workitem})")
        self._pomodoro = pomodoro
        self._workitem = workitem
        self._state = 'rest'
        self._planned_duration = rest_duration
        self._remaining_duration = rest_duration
        logger.debug(f'PomodoroTimer: Before emitting TimerWorkComplete')
        self._emit(PomodoroTimer.TimerWorkComplete, {
            'timer': self,
        }, None)
        logger.debug(f'PomodoroTimer: Before scheduling transition to finished')
        self._schedule_transition(rest_duration * 1000, pomodoro, workitem, 'finished')
        logger.debug(f'PomodoroTimer: Done - Handling rest start')

    def _handle_pomodoro_complete(self,
                                  event: str,
                                  pomodoro: Pomodoro,
                                  workitem: Workitem,
                                  **kwargs) -> None:
        logger.debug(f'PomodoroTimer: Handling pomodoro complete or void')
        if pomodoro != self._pomodoro:
            logger.warning("PomodoroTimer: Warning - Timer detected completion of an unexpected pomodoro")
        if workitem != self._workitem:
            logger.warning(f"PomodoroTimer: Warning - Timer detected completion of an unexpected workitem ({workitem} != {self._workitem})")
        last_pomodoro = self._pomodoro
        self._pomodoro = None
        last_workitem = self._workitem
        self._workitem = None
        self._state = 'idle'
        self._planned_duration = 0
        self._remaining_duration = 0
        self._emit(PomodoroTimer.TimerRestComplete, {
            'timer': self,
            'pomodoro': last_pomodoro,
            'workitem': last_workitem,
        }, None)
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

    def get_running_workitem(self) -> Workitem:
        return self._workitem

    def get_running_pomodoro(self) -> Pomodoro:
        return self._pomodoro

    def is_working(self) -> bool:
        return self._state == 'work'

    def is_resting(self) -> bool:
        return self._state == 'rest'

    def is_idling(self) -> bool:
        return self._state == 'idle'

    def is_initializing(self) -> bool:
        return self._state is None

    def get_planned_duration(self) -> int:
        return self._planned_duration

    def get_remaining_duration(self) -> float:
        return self._remaining_duration

    def get_elapsed_duration(self) -> float:
        return self._pomodoro.get_elapsed_duration()

    def format_remaining_duration(self) -> str:
        remaining_duration = self.get_remaining_duration()     # This is always >= 0
        remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
        remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
        return f'{remaining_minutes}:{remaining_seconds}'

    def format_elapsed_duration(self) -> str:
        elapsed_duration = int(self.get_elapsed_duration())     # This is always >= 0
        td = timedelta(seconds=elapsed_duration)
        return f'{td}'

    def get_completion(self) -> float:
        planned = self.get_planned_duration()
        return self.get_remaining_duration() / planned if planned > 0 else 0

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

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_timer import AbstractTimer
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import CompletePomodoroStrategy, StartRestStrategy
from fk.core.workitem import Workitem


# This timer never goes below 0
# TODO: Currently we use source.on() to subscribe to its events
# See how we can use this class instead, i.e. timer.on()
class PomodoroTimer(AbstractEventEmitter):
    _source: AbstractEventSource
    _tick_timer: AbstractTimer
    _transition_timer: AbstractTimer
    _state: str | None
    _pomodoro: Pomodoro | None
    _workitem: Workitem | None
    _planned_duration: int
    _remaining_duration: float

    # Emitted events
    TimerTick = "TimerTick"
    TimerWorkStart = "TimerWorkStart"
    TimerWorkComplete = "TimerWorkComplete"
    TimerRestComplete = "TimerRestComplete"

    def __init__(self,
                 source: AbstractEventSource,
                 tick_timer: AbstractTimer,
                 transition_timer: AbstractTimer):
        super().__init__(['TimerTick', 'TimerWorkStart', 'TimerWorkComplete', 'TimerRestComplete'],
                         source.get_settings().invoke_callback)
        print('PomodoroTimer: Initializing')
        self._source = source
        self._tick_timer = tick_timer
        self._transition_timer = transition_timer

        self._state = None
        self._pomodoro = None
        self._workitem = None
        self._planned_duration = 0
        self._remaining_duration = 0

        self._refresh()

        # Start tracking changes and initialize with the latest state
        print('PomodoroTimer: Connecting')
        source.on(events.AfterPomodoroWorkStart, self._handle_pomodoro_work_start)
        source.on(events.AfterPomodoroRestStart, self._handle_pomodoro_rest_start)
        source.on(events.AfterPomodoroComplete, self._handle_pomodoro_complete)
        print('PomodoroTimer: Initialized')

    def _refresh(self) -> None:
        print('PomodoroTimer: Refreshing')
        workitem: Workitem | None = None
        pomodoro: Pomodoro | None = None
        for backlog in self._source.backlogs():
            w, p = backlog.get_running_workitem()
            if w is not None:
                workitem = w
                pomodoro = p
                break

        if workitem is None:
            print('PomodoroTimer: Currently idle')
            self._state = 'idle'    # work, rest, idle
            self._pomodoro = None
            self._workitem = None
            self._planned_duration = 0
            self._remaining_duration = 0
            self._transition_timer.cancel()
            self._tick_timer.cancel()
        elif workitem is not None and pomodoro is not None:
            self._state = 'rest' if pomodoro.is_resting() else 'work'
            print(f'PomodoroTimer: Currently {self._state}')
            self._pomodoro = pomodoro
            self._workitem = workitem
            self._planned_duration = pomodoro.get_rest_duration() \
                if pomodoro.is_resting() else pomodoro.get_work_duration()
            self._remaining_duration = max(pomodoro.remaining_time_in_current_state(), 0)
            self._transition_timer.cancel()
            if self._remaining_duration > 0:
                self._schedule_tick()
                if pomodoro.is_working():
                    print(f'PomodoroTimer: Is working')
                    self._schedule_transition(
                        self._remaining_duration * 1000,
                        pomodoro,
                        workitem,
                        'rest')
                elif pomodoro.is_resting():
                    print(f'PomodoroTimer: Is resting')
                    self._schedule_transition(
                        self._remaining_duration * 1000,
                        pomodoro,
                        workitem,
                        'finished')
                else:
                    raise Exception(f'Unexpected running state: {pomodoro.get_state()}')

    def __str__(self):
        return f'Timer is {self._state}'

    def _schedule_tick(self) -> None:
        self._tick_timer.schedule(990, self._handle_tick, None)

    def _handle_tick(self, params: dict | None) -> None:
        if self._pomodoro is not None:
            self._remaining_duration = max(self._pomodoro.remaining_time_in_current_state(), 0)
            # Only tick if there's something running
            self._emit(PomodoroTimer.TimerTick, {
                'timer': self,
            })

    def _schedule_transition(self,
                             ms: float,
                             target_pomodoro: Pomodoro,
                             target_workitem: Workitem,
                             target_state: str) -> None:
        print(f'PomodoroTimer: Scheduled transition to {target_state} in {ms / 1000} seconds')
        self._transition_timer.schedule(ms, self._handle_transition, {
            'target_pomodoro': target_pomodoro,
            'target_workitem': target_workitem,
            'target_state': target_state,
        }, True)
        print(f'PomodoroTimer: Done - Scheduled transition to {target_state} in {ms / 1000} seconds')

    def _handle_transition(self, params: dict | None) -> None:
        target_pomodoro: Pomodoro = params['target_pomodoro']
        target_workitem: Workitem = params['target_workitem']
        target_state: str = params['target_state']
        print(f'PomodoroTimer: Handling transition from {self._state} to {target_state}')
        if target_pomodoro.is_canceled() or target_pomodoro.is_finished():
            # We've already sealed this pomodoro, nothing else to do
            print(f"We've already sealed this pomodoro, nothing else to do")
            return
        if target_state == 'rest':
            # Getting fresh rest duration in case it changed since the pomodoro was created.
            # Note that we get the fresh work duration as soon as the work starts (see get_work_duration()).
            rest_duration = self._source.get_config_parameter('Pomodoro.default_rest_duration')
            print(f"Will execute StartRestStrategy('{target_workitem.get_name()}', '{rest_duration}')")
            self._source.execute(
                StartRestStrategy,
                [target_workitem.get_uid(), rest_duration]
            )
            print(f"PomodoroTimer: Executed StartRestStrategy")
        elif target_state == 'finished':
            print(f"PomodoroTimer: Will execute CompletePomodoroStrategy('{target_workitem.get_name()}', 'finished')")
            self._source.execute(
                CompletePomodoroStrategy,
                [target_workitem.get_uid(), "finished"]
            )
            print(f"PomodoroTimer: Executed CompletePomodoroStrategy")
        else:
            raise Exception(f"Unexpected scheduled transition state: {target_state}")
        print(f'PomodoroTimer: Done - Handling transition to {target_state}')

    def _handle_pomodoro_work_start(self,
                                    event: str,
                                    pomodoro: Pomodoro,
                                    workitem: Workitem,
                                    work_duration: int) -> None:
        print(f'Handling work start')
        self._pomodoro = pomodoro
        self._workitem = workitem
        self._state = 'work'
        self._planned_duration = work_duration
        self._remaining_duration = work_duration
        self._emit(PomodoroTimer.TimerWorkStart, {
            'timer': self,
        })
        self._schedule_transition(work_duration * 1000, pomodoro, workitem, 'rest')
        self._schedule_tick()
        print(f'PomodoroTimer: Done - Handling work start')

    def _handle_pomodoro_rest_start(self,
                                    event: str,
                                    pomodoro: Pomodoro,
                                    workitem: Workitem,
                                    rest_duration: int) -> None:
        print(f'PomodoroTimer: Handling rest start')
        if pomodoro != self._pomodoro:
            print("PomodoroTimer: Warning - Timer detected start of an unexpected pomodoro")
        if workitem != self._workitem:
            print(f"PomodoroTimer: Warning - Timer detected start of an unexpected workitem ({workitem} != {self._workitem})")
        self._pomodoro = pomodoro
        self._workitem = workitem
        self._state = 'rest'
        self._planned_duration = rest_duration
        self._remaining_duration = rest_duration
        print(f'PomodoroTimer: Before emitting TimerWorkComplete')
        self._emit(PomodoroTimer.TimerWorkComplete, {
            'timer': self,
        })
        print(f'PomodoroTimer: Before scheduling transition to finished')
        self._schedule_transition(rest_duration * 1000, pomodoro, workitem, 'finished')
        print(f'PomodoroTimer: Done - Handling rest start')

    def _handle_pomodoro_complete(self,
                                  event: str,
                                  pomodoro: Pomodoro,
                                  workitem: Workitem,
                                  target_state: str) -> None:
        print(f'PomodoroTimer: Handling pomodoro complete')
        if pomodoro != self._pomodoro:
            print("PomodoroTimer: Warning - Timer detected completion of an unexpected pomodoro")
        if workitem != self._workitem:
            print(f"PomodoroTimer: Warning - Timer detected completion of an unexpected workitem ({workitem} != {self._workitem})")
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
        })
        # It might look better to just check for the terminal conditions directly in the handlers instead
        # of canceling timers here. We are going the latter path to account for scenarios when stuff gets
        # void because of cascading deletes. For instance, if we delete a Workitem with a running pomodoro,
        # the latter is canceled automatically. If we were to check this in the handler, we would've been
        # ticking and running stuff against zombie objects, which might be dangerous form the data
        # consistency point of view.
        self._transition_timer.cancel()
        self._tick_timer.cancel()
        print('PomodoroTimer: Canceled transition timer')
        print(f'PomodoroTimer: Done - Handling pomodoro complete')

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

    def get_planned_duration(self) -> int:
        return self._planned_duration

    def get_remaining_duration(self) -> float:
        return self._remaining_duration

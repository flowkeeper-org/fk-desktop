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
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemDelete, AfterWorkitemComplete, AfterWorkitemRename, AfterPomodoroRemove, \
    SourceMessagesProcessed
from fk.core.pomodoro import Pomodoro
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem


class AbstractTimerDisplay:
    """A timer can be in one of the five modes -- undefined, idle, working, resting and standby AKA
    "Ready to start another Pomodoro?" mode."""

    _source_holder: EventSourceHolder
    _timer: PomodoroTimer
    _continue_workitem: Workitem | None
    _mode: str

    def __init__(self,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder):
        self._source_holder = source_holder
        self._timer = timer
        self._continue_workitem = None
        self._mode = "undefined"

        timer.on(PomodoroTimer.TimerWorkStart, self._on_work_start)
        timer.on(PomodoroTimer.TimerWorkComplete, self._on_work_complete)
        timer.on(PomodoroTimer.TimerRestComplete, lambda workitem, **kwargs: self.rest_complete(workitem))
        timer.on(PomodoroTimer.TimerTick, self._on_tick)
        timer.on(PomodoroTimer.TimerInitialized, self._on_timer_initialized)

        source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _set_mode(self, mode):
        old_mode = self._mode
        if old_mode != mode:
            self._mode = mode
            self.mode_changed(old_mode, mode)

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        source.on(AfterWorkitemDelete,
                  lambda workitem, **kwargs: self.reset() if workitem == self._continue_workitem else None)
        source.on(AfterWorkitemComplete,
                  lambda workitem, **kwargs: self.reset() if workitem == self._continue_workitem else None)

        # Not sure how to handle it best here
        # TODO: Another bug -- "Start another" shows if we complete a workitem while it's running
        # TODO: Another bug -- "Start another" shows if we delete a workitem while it's running
        source.on(AfterWorkitemRename,
                  lambda workitem, **kwargs: None)
        source.on(AfterPomodoroRemove,
                  lambda workitem, **kwargs: None)

    def _on_timer_initialized(self, event: str, timer: PomodoroTimer) -> None:
        if timer.is_resting():
            self._set_mode('resting')
            self._on_work_start()
        elif timer.is_working():
            self._set_mode('working')
            self._on_work_start()
        else:
            self._set_mode('idle')
            self.reset()

    def _on_tick(self, pomodoro: Pomodoro, **kwargs) -> None:
        state = 'Focus' if self._timer.is_working() else 'Rest'
        state_text = f"{state}: {self._timer.format_remaining_duration()} left"
        self.tick(pomodoro, state_text, self._timer.get_completion())

    def _on_work_start(self, **kwargs) -> None:
        self._continue_workitem = self._timer.get_running_workitem()
        self._on_tick(self._timer.get_running_pomodoro())
        self.work_start(self._continue_workitem)

    def _on_work_complete(self, **kwargs) -> None:
        self._on_tick(self._timer.get_running_pomodoro())
        self.work_complete()
        if self._mode != 'resting':
            self.mode_changed(self._mode, 'resting')

    # Override those in the child widgets

    def reset(self, **kwargs):
        pass

    def tick(self, pomodoro: Pomodoro, state_text: str, completion: float) -> None:
        pass

    def work_start(self, item: Workitem) -> None:
        pass

    def work_complete(self) -> None:
        pass

    def rest_complete(self, workitem: Workitem) -> None:
        pass

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        pass

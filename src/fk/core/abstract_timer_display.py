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

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemDelete, AfterWorkitemComplete, AfterPomodoroRemove
from fk.core.pomodoro import Pomodoro
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)


class AbstractTimerDisplay:
    """A timer can be in one of the five modes -- undefined, idle, working, resting and ready AKA
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
        self._mode = 'undefined'

        timer.on(PomodoroTimer.TimerWorkStart, self._on_work_start)
        timer.on(PomodoroTimer.TimerWorkComplete, self._on_work_complete)
        timer.on(PomodoroTimer.TimerRestComplete, self._on_rest_complete)
        timer.on(PomodoroTimer.TimerTick, self._on_tick)
        timer.on(PomodoroTimer.TimerInitialized, self._on_timer_initialized)

        source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _set_mode(self, mode):
        old_mode = self._mode
        if old_mode != mode:
            # Check forbidden mode transitions
            if (old_mode == 'resting' and mode == 'working') or \
                    (old_mode == 'idle' and mode == 'resting') or \
                    (old_mode == 'idle' and mode == 'ready'):
                raise Exception(f'Encountered impossible timer mode change from {old_mode} to {mode}')
            self._mode = mode
            self.mode_changed(old_mode, mode)
            logger.debug(f'Timer display mode changed from {old_mode} to {mode}')
            if mode == 'working' or mode == 'resting':
                self._on_tick(self._timer.get_running_pomodoro())

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        self._continue_workitem = None
        self._set_mode('undefined')

        source.on(AfterWorkitemComplete, self._on_workitem_complete_or_delete)
        source.on(AfterWorkitemDelete, self._on_workitem_complete_or_delete)
        source.on(AfterPomodoroRemove, self._on_pomodoro_remove)

    def _on_timer_initialized(self, event: str, timer: PomodoroTimer) -> None:
        if timer.is_resting():
            self._on_work_complete()
        elif timer.is_working():
            self._on_work_start()
        else:
            self._continue_workitem = None
            self._set_mode('idle')

    def _on_tick(self, pomodoro: Pomodoro, **kwargs) -> None:
        state = 'Focus' if self._timer.is_working() else 'Rest'
        state_text = f"{state}: {self._timer.format_remaining_duration()} left"
        self.tick(pomodoro, state_text, self._timer.get_completion())

    def _on_work_start(self, **kwargs) -> None:
        self._continue_workitem = self._timer.get_running_workitem()
        self._set_mode('working')

    def _on_work_complete(self, **kwargs) -> None:
        self._continue_workitem = self._timer.get_running_workitem()
        self._set_mode('resting')

    def _on_rest_complete(self, workitem: Workitem, **kwargs) -> None:
        if self._continue_workitem is not None and workitem.is_startable():
            self._set_mode('ready')
        else:
            self._continue_workitem = None
            self._set_mode('idle')

    def _on_workitem_complete_or_delete(self, workitem: Workitem, **kwargs) -> None:
        if workitem == self._continue_workitem:
            self._continue_workitem = None
            self._set_mode('idle')

    def _on_pomodoro_remove(self, workitem: Workitem, **kwargs) -> None:
        if workitem == self._continue_workitem \
                and self._timer.is_idling() \
                and not workitem.is_startable():
            self._continue_workitem = None
            self._set_mode('idle')

    # Override those in the child widgets

    def tick(self, pomodoro: Pomodoro, state_text: str, completion: float) -> None:
        pass

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        pass

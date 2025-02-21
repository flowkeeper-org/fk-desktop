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

from fk.core.abstract_data_item import AbstractDataItem, generate_uid
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)


class TimerData(AbstractDataItem['User']):
    # State is one of the following: work, rest, idle
    _state: str | None
    _pomodoro: Pomodoro | None
    _planned_duration: float
    _remaining_duration: float
    _last_state_change: datetime.datetime | None
    _next_state_change: datetime.datetime | None

    def __init__(self,
                 user: 'User',
                 create_date: datetime.datetime):
        super().__init__(uid=generate_uid(), parent=user, create_date=create_date)
        self._state = 'idle'
        self._pomodoro = None
        self._planned_duration = 0
        self._remaining_duration = 0
        self._last_state_change = None
        self._next_state_change = None

    def get_running_pomodoro(self) -> Pomodoro | None:
        return self._pomodoro

    def get_running_workitem(self) -> Workitem | None:
        return self._pomodoro.get_parent() if self._pomodoro is not None else None

    def get_state(self) -> str:
        return self._state

    def idle(self, when: datetime.datetime | None = None) -> None:
        self._state = 'idle'
        self._pomodoro = None
        self._planned_duration = 0
        self._remaining_duration = 0
        self._last_state_change = datetime.datetime.now(datetime.timezone.utc) if when is None else when
        self._next_state_change = None

    def work(self, pomodoro: Pomodoro, work_duration: float, when: datetime.datetime | None = None) -> None:
        self._state = 'work'
        self._pomodoro = pomodoro
        self._planned_duration = work_duration
        self._remaining_duration = work_duration
        self._last_state_change = datetime.datetime.now(datetime.timezone.utc) if when is None else when
        if work_duration:   # It might be 0 for tracker workitems
            self._next_state_change = self._last_state_change + datetime.timedelta(seconds=work_duration)
        else:
            self._next_state_change = None

    def rest(self, rest_duration: float, when: datetime.datetime | None = None) -> None:
        self._state = 'rest'
        self._planned_duration = rest_duration
        self._remaining_duration = rest_duration
        self._last_state_change = datetime.datetime.now(datetime.timezone.utc) if when is None else when
        if rest_duration:   # It might be 0 for long / unlimited breaks
            self._next_state_change = self._last_state_change + datetime.timedelta(seconds=rest_duration)
        else:
            self._next_state_change = None

    def is_working(self) -> bool:
        return self._state == 'work'

    def is_resting(self) -> bool:
        return self._state == 'rest'

    def is_idling(self) -> bool:
        return self._state == 'idle'

    def is_ticking(self) -> bool:
        return self._state != 'idle'

    def is_initializing(self) -> bool:
        return self._state is None

    def get_planned_duration(self) -> int:
        return self._planned_duration

    def get_remaining_duration(self) -> float:
        return self._remaining_duration

    def get_elapsed_duration(self) -> float:
        return self._pomodoro.get_elapsed_duration()

    def get_next_state_change(self) -> datetime.datetime | None:
        return self._next_state_change

    def format_remaining_duration(self) -> str:
        remaining_duration = self.get_remaining_duration()     # This is always >= 0
        remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
        remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
        return f'{remaining_minutes}:{remaining_seconds}'

    def format_elapsed_duration(self) -> str:
        elapsed_duration = int(self.get_elapsed_duration())     # This is always >= 0
        td = datetime.timedelta(seconds=elapsed_duration)
        return f'{td}'

    def __str__(self) -> str:
        s = 'no pomodoro'
        if self._pomodoro is not None:
            s = 'workitem' + str(self._pomodoro.get_parent())
        return f'Timer for user {self.get_parent().get_identity()}, {s}. ' \
               f'State "{self._state}", ' \
               f'started at {self._last_state_change}, ' \
               f'next ring at {self._next_state_change}'

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

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_data_item import generate_uid
from fk.core.interruption import Interruption

logger = logging.getLogger(__name__)


POMODORO_TYPE_NORMAL = 'normal'
POMODORO_TYPE_TRACKER = 'tracker'
POMODORO_TYPE_COUNTER = 'counter'


class Pomodoro(AbstractDataContainer[Interruption, 'Workitem']):
    _is_planned: bool
    _state: str
    _type: str
    _work_duration: float
    _rest_duration: float
    _date_work_started: datetime.datetime | None
    _date_rest_started: datetime.datetime | None
    _date_completed: datetime.datetime | None

    # State is one of the following: new, work, rest, finished
    def __init__(self,
                 number: int,
                 is_planned: bool,
                 state: str,
                 work_duration: float,
                 rest_duration: float,
                 type_: str,
                 uid: str,
                 workitem: 'Workitem',
                 create_date: datetime.datetime):
        super().__init__(name=f'Pomodoro {number}', uid=uid, parent=workitem, create_date=create_date)
        self._is_planned = is_planned
        self._state = state
        self._type = type_
        self._work_duration = work_duration
        self._rest_duration = rest_duration
        self._date_work_started = None
        self._date_rest_started = None
        self._date_completed = None

    def __str__(self):
        if self.is_startable():
            char = '[ ]' if self._is_planned else '( )'
        elif self.is_running():
            # Here we don't distinguish between work and rest
            char = '[#]' if self._is_planned else '(#)'
        elif self.is_finished():
            char = '[v]' if self._is_planned else '(v)'
        else:
            raise Exception(f'Invalid pomodoro state: {self._state}')
        return char

    def update_work_duration(self, work_duration: float) -> None:
        if self.is_startable():
            self._work_duration = work_duration
        else:
            raise Exception(f'Trying to update work duration of a pomodoro in state {self._state}')

    def get_state(self) -> str:
        return self._state

    def get_work_start_date(self) -> datetime.datetime:
        return self._date_work_started

    def get_rest_start_date(self) -> datetime.datetime:
        if self._type == POMODORO_TYPE_NORMAL:
            return self._date_rest_started
        else:
            raise Exception(f"Pomodoros of type {self._type} don't support rest")

    def update_rest_duration(self, rest_duration: float) -> None:
        if self.is_startable() or self.is_working():
            self._rest_duration = rest_duration
        else:
            raise Exception(f'Trying to update rest duration of a pomodoro in state {self._state}')

    def seal(self, when: datetime.datetime) -> None:
        if self._type == POMODORO_TYPE_NORMAL:
            if self.is_resting():
                self._state = 'finished'
                self._date_completed = when
                self._last_modified_date = when
            elif self.is_working():
                # This is a rare corner case, which we may encounter in the field. The client went down while
                # the pomodoro was in work, and came back up when it was in rest. The timer then transitioned
                # it to Finished state correctly. This results in a missing "StartRest" historical record.
                # We can work around this situation reliably if the Finish happened "after" the work + rest
                # should've finished (take into account some little margin for error, just a few seconds).
                if when > self.planned_end_of_rest() - datetime.timedelta(seconds=5):
                    logger.debug(f"Warning - skipped rest for a pomodoro on {self.get_parent().get_name()}, but still "
                                 "authorized its completion (transition happened when the client was offline)")
                    self._state = 'finished'
                    self._date_completed = when
                    self._last_modified_date = when
            else:
                raise Exception(f'Cannot seal normal pomodoro from {self._state}')
        elif self._type == POMODORO_TYPE_TRACKER:
            if self.is_working():
                self._state = 'finished'
                self._date_completed = when
                self._last_modified_date = when
            else:
                raise Exception(f'Cannot seal tracker pomodoro from {self._state}')
        elif self._type == POMODORO_TYPE_COUNTER:
            raise Exception(f'Cannot seal counter pomodoro')

    def void(self, when: datetime.datetime) -> None:
        if self._type == POMODORO_TYPE_NORMAL:
            if self.is_resting() or self.is_working():
                self._state = 'new'
                self._last_modified_date = when
            else:
                raise Exception(f'Cannot void normal pomodoro from {self._state}')
        else:
            raise Exception(f'Cannot void pomodoro of type {self._type}')

    def start_work(self, when: datetime.datetime) -> None:
        if self._type != POMODORO_TYPE_COUNTER:
            self._state = 'work'
            self._date_work_started = when
            self._last_modified_date = when
        else:
            raise Exception(f"Pomodoros of type counter don't have work")

    def start_rest(self, when: datetime.datetime) -> None:
        if self._type == POMODORO_TYPE_NORMAL:
            self._state = 'rest'
            self._date_rest_started = when
            self._last_modified_date = when
        else:
            raise Exception(f"Pomodoros of type {self._type} don't support rest")

    def is_running(self) -> bool:
        return self._state == 'work' or self._state == 'rest'

    def is_startable(self) -> bool:
        return self._state == 'new'

    def is_working(self) -> bool:
        if self._type != POMODORO_TYPE_COUNTER:
            return self._state == 'work'
        else:
            raise Exception(f"Pomodoros of type counter don't have work")

    def is_resting(self) -> bool:
        if self._type == POMODORO_TYPE_NORMAL:
            return self._state == 'rest'
        else:
            raise Exception(f"Pomodoros of type {self._type} don't have rest")

    def is_finished(self) -> bool:
        return self._state == 'finished'

    def get_elapsed_duration(self, when: datetime.datetime = None) -> float:
        if self._date_work_started is not None:
            if self.is_working():
                now = datetime.datetime.now(datetime.timezone.utc) if when is None else when
            elif self.is_finished():
                now = self._last_modified_date
            return (now - self._date_work_started).total_seconds()
        else:
            return 0

    def get_work_duration(self, when: datetime.datetime = None) -> float:
        if self._type == POMODORO_TYPE_NORMAL:
            return self._work_duration
        elif self._type == POMODORO_TYPE_TRACKER:
            if self.is_working():
                return self.get_elapsed_duration(when)
            elif self.is_startable():
                return 0
            else:
                return (self._date_completed - self._date_work_started).total_seconds()
        elif self._type == POMODORO_TYPE_COUNTER:
            raise Exception(f"Pomodoros of type counter don't have work")

    def get_rest_duration(self) -> float:
        if self._type == POMODORO_TYPE_NORMAL:
            return self._rest_duration
        else:
            raise Exception(f"Pomodoros of type {self._type} don't have rest")

    def get_type(self):
        return self._type

    def total_remaining_time(self, when: datetime.datetime) -> float:
        # Total remaining time in seconds, which only makes sense for active pomodoros.
        # Can be negative, if it has expired. Can be 0, if it hasn't started yet.
        remaining_in_current = self.remaining_time_in_current_state(when)
        if self.is_working():
            return remaining_in_current + self._rest_duration
        else:
            return remaining_in_current

    def remaining_time_in_current_state(self, when: datetime.datetime) -> float:
        if self._type == POMODORO_TYPE_NORMAL:
            # Remaining time in the current state in seconds.
            # Can be negative, if it has expired.
            # Will be 0 if it hasn't started yet.
            if self.is_working():
                now = datetime.datetime.now(datetime.timezone.utc) if when is None else when
                return (self.planned_end_of_work() - now).total_seconds()
            elif self.is_resting():
                now = datetime.datetime.now(datetime.timezone.utc) if when is None else when
                return (self.planned_end_of_rest() - now).total_seconds()
            else:
                return 0
        else:
            raise Exception(f"Pomodoros of type {self._type} don't have remaining time")

    def remaining_minutes_in_current_state_str(self, when: datetime.datetime) -> str:
        seconds = self.remaining_time_in_current_state(when)
        if seconds == 0:
            return 'N/A'
        m = seconds / 60
        if m < 1:
            return "Less than a minute"
        else:
            return f"{round(m)} minutes"

    def planned_time_in_current_state(self) -> float:
        if self._type == POMODORO_TYPE_NORMAL:
            # Planned time in the current state in seconds. Will be 0 if this pomodoro is
            # sealed or hasn't started yet.
            if self.is_resting():
                return self._rest_duration
            elif self.is_working():
                return self._work_duration
            else:
                return 0
        else:
            raise Exception(f"Pomodoros of type {self._type} don't have planned time")

    def planned_end_of_work(self) -> datetime.datetime:
        if self._type == POMODORO_TYPE_NORMAL:
            if self._date_work_started is None:
                return None
            return self._date_work_started + datetime.timedelta(seconds=self._work_duration)
        else:
            raise Exception(f"Pomodoros of type {self._type} don't have planned time")

    def planned_end_of_rest(self) -> datetime.datetime:
        if self._date_work_started is None:
            return None
        return self.planned_end_of_work() + datetime.timedelta(seconds=self._rest_duration)

    def total_planned_time(self) -> float:
        # Total planned time in seconds. Can be None, if this pomodoro is sealed or hasn't started yet.
        planned_in_current = self.planned_time_in_current_state()
        if self.is_working():
            return planned_in_current + self._rest_duration
        else:
            return planned_in_current

    def get_parent(self) -> 'Workitem':
        return self._parent

    def dump(self, indent: str = '', mask_uid: bool = False) -> str:
        return f'{super().dump(indent, True)}\n' \
               f'{indent}  Type: {self._type}\n' \
               f'{indent}  State: {self._state}\n' \
               f'{indent}  Is planned: {self._is_planned}\n' \
               f'{indent}  Work duration: {self._work_duration}\n' \
               f'{indent}  Rest duration: {self._rest_duration}\n' \
               f'{indent}  Work started: {self._date_work_started}\n' \
               f'{indent}  Rest started: {self._date_rest_started}\n' \
               f'{indent}  Completed: {self._date_completed}'

    def add_interruption(self, reason: str | None, duration: datetime.timedelta | None, void: bool, when: datetime.datetime) -> None:
        uid = generate_uid()
        self[uid] = Interruption(reason, duration, void, uid, self, when)

    def is_planned(self) -> bool:
        return self._is_planned

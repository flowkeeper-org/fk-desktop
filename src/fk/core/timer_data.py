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
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL
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
    _last_date: datetime.date
    _pomodoro_in_series: int

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
        self._last_date = datetime.date.today()
        self._pomodoro_in_series = 0

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
        self.item_updated(when)
        logger.debug(f'Timer: Transitioned to idle at {self._last_state_change}')

    def work(self, pomodoro: Pomodoro, work_duration: float, when: datetime.datetime | None = None) -> None:
        self._state = 'work'
        self._pomodoro = pomodoro
        self._planned_duration = work_duration
        self._remaining_duration = work_duration
        self._last_state_change = datetime.datetime.now(datetime.timezone.utc) if when is None else when
        if work_duration and pomodoro.get_type() == POMODORO_TYPE_NORMAL:   # It might be 0 for tracker workitems
            self._next_state_change = self._last_state_change + datetime.timedelta(seconds=work_duration)
        else:
            self._next_state_change = None
        self.item_updated(when)
        logger.debug(f'Timer: Transitioned to work at {self._last_state_change}. '
                     f'Next state change: {self._next_state_change}')

    def _refresh_today(self, when: datetime.datetime | None = None):
        if when is None:
            when = datetime.datetime.now()
        today = when.date()
        if self._last_date != today:
            self._last_date = today
            self._pomodoro_in_series = 0
            logger.debug('Reset pomodoro series because we started a new day')

    def rest(self, rest_duration: float, when: datetime.datetime | None = None) -> None:
        self._state = 'rest'
        self._planned_duration = rest_duration
        self._remaining_duration = rest_duration
        self._last_state_change = datetime.datetime.now(datetime.timezone.utc) if when is None else when

        self._refresh_today(when)  # Reset the series, if needed

        if rest_duration > 0 and self._pomodoro.get_type() == POMODORO_TYPE_NORMAL:   # It might be 0 for long / unlimited breaks
            self._next_state_change = self._last_state_change + datetime.timedelta(seconds=rest_duration)
            self._pomodoro_in_series += 1  # Increment the number of completed pomodoros in series
        else:
            self._next_state_change = None
            self._pomodoro_in_series = 0  # We started a long break, can now reset the series

        self.item_updated(when)

        logger.debug(f'Timer: Transitioned to rest at {self._last_state_change}. '
                     f'Next state change: {self._next_state_change}. '
                     f'Pomodoros in series: {self._pomodoro_in_series}.')

    def is_working(self) -> bool:
        return self._state == 'work'

    def is_resting(self) -> bool:
        return self._state == 'rest'

    def is_idling(self) -> bool:
        return self._state == 'idle'

    def is_ticking(self) -> bool:
        return self._state != 'idle'

    def get_planned_duration(self) -> int:
        return self._planned_duration

    def get_remaining_duration(self) -> float:
        return self._remaining_duration

    def get_next_state_change(self) -> datetime.datetime | None:
        return self._next_state_change

    # There's no "when" parameter, because it assumes we call update_remaining_duration first
    def format_remaining_duration(self) -> str:
        remaining_duration = self.get_remaining_duration()     # This is always >= 0
        remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
        remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
        return f'{remaining_minutes}:{remaining_seconds}'

    def format_elapsed_work_duration(self, when: datetime.datetime | None = None) -> str:
        if self._pomodoro is None:
            return 'N/A'
        else:
            elapsed_duration = int(self._pomodoro.get_elapsed_work_duration(when))
            td = datetime.timedelta(seconds=elapsed_duration)
            return f'{td}'

    def format_elapsed_rest_duration(self, when: datetime.datetime | None = None) -> str:
        if self._pomodoro is None:
            return 'N/A'
        else:
            elapsed_duration = int(self._pomodoro.get_elapsed_rest_duration(when))
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

    def update_remaining_duration(self, when: datetime.datetime | None):
        if self._next_state_change is not None:
            now = when if when is not None else datetime.datetime.now(datetime.timezone.utc)
            if now < self._next_state_change:
                self._remaining_duration = (self._next_state_change - now).total_seconds()
            else:
                self._remaining_duration = 0
        self.item_updated(when)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['state'] = self._state
        d['pomodoro'] = self._pomodoro.get_uid() if self._pomodoro is not None else None
        d['planned_duration'] = self._planned_duration
        d['remaining_duration'] = self._remaining_duration
        d['last_state_change'] = self._last_state_change
        d['next_state_change'] = self._next_state_change
        return d

    def get_pomodoro_in_series(self) -> int:
        self._refresh_today()
        return self._pomodoro_in_series

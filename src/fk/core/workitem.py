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

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_data_item import generate_uid
from fk.core.pomodoro import Pomodoro


class Workitem(AbstractDataContainer[Pomodoro, 'Backlog']):
    # State is one of the following: new, running, finished, canceled
    _state: str
    _date_work_started: datetime.datetime | None
    _date_work_ended: datetime.datetime | None

    def __init__(self,
                 name: str,
                 uid: str,
                 backlog: 'Backlog',
                 create_date: datetime.datetime):
        super().__init__(name=name, parent=backlog, uid=uid, create_date=create_date)
        self._state = 'new'
        self._date_work_started = None
        self._date_work_ended = None

    def __str__(self):
        if self._state == 'new':
            char = ' '
        elif self._state == 'running':
            char = '*'
        elif self._state == 'finished':
            char = '✓'
        elif self._state == 'canceled':
            char = 'X'
        else:
            raise Exception(f'Invalid workitem state:{self._state}')

        return f' - [{char}] {self._name} {"".join([str(p) for p in self.values()])}'

    def seal(self, target_state: str, when: datetime.datetime) -> None:
        if target_state in ('finished', 'canceled'):
            self._state = target_state
            self._date_work_ended = when
        else:
            raise Exception(f'Invalid workitem state: {target_state}')

    def add_pomodoro(self,
                     num_pomodoros: int,
                     default_work_duration: int,
                     default_rest_duration: int,
                     when: datetime.datetime) -> None:
        is_planned = not self.is_running()
        for i in range(num_pomodoros):
            # At the planning stage we create Pomodoros with the default work and rest
            # durations, because that's the best info we have. However, when we start
            # a Pomodoro, this duration can be updated.
            # Also, note that here we don't emit AddPomodoro events.
            uid = generate_uid()
            self[uid] = Pomodoro(
                is_planned,
                'new',
                default_work_duration,
                default_rest_duration,
                uid,
                self,
                when)

    def remove_pomodoro(self, pomodoro: Pomodoro) -> None:
        del self[pomodoro.get_uid()]

    def is_running(self) -> bool:
        return self._state == 'running'

    def has_running_pomodoro(self) -> bool:
        for p in self.values():
            if p.is_running():
                return True
        return False

    def is_sealed(self) -> bool:
        return self._state in ('finished', 'canceled')

    def is_planned(self) -> bool:
        # TODO: Calculate it based on the parent's state
        return True

    def is_startable(self) -> bool:
        for p in self.values():
            if p.is_startable():
                return True
        return False

    def start(self, when: datetime.datetime) -> None:
        self._state = 'running'
        self._date_work_started = when

    def dump(self, indent: str = '') -> str:
        return f'{super().dump(indent)}\n' \
               f'{indent} - State: {self._state}\n' \
               f'{indent} - Work started: {self._date_work_started}\n' \
               f'{indent} - Work ended: {self._date_work_ended}'

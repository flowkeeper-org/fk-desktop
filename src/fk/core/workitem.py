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
import re
import textwrap
from collections.abc import Set
from typing import Iterable

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_data_item import generate_uid
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_TRACKER

TAG_REGEX = re.compile('#(\\w+)')


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
                     default_work_duration: float,
                     default_rest_duration: float,
                     type_: str,
                     when: datetime.datetime) -> None:
        is_planned = not self.is_running()
        existing = len(self)
        for i in range(num_pomodoros):
            # At the planning stage we create Pomodoros with the default work and rest
            # durations, because that's the best info we have. However, when we start
            # a Pomodoro, this duration can be updated.
            # Also, note that here we don't emit AddPomodoro events.
            uid = generate_uid()
            self[uid] = Pomodoro(
                existing + i + 1,
                is_planned,
                'new',
                default_work_duration,
                default_rest_duration,
                type_,
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
        backlog_start_date = self.get_parent().get_start_date()
        if backlog_start_date is None:
            return True
        else:
            return self.get_create_date() <= backlog_start_date

    def is_startable(self) -> bool:
        if not self.is_sealed():
            for p in self.values():
                if p.is_startable():
                    return True
        return False

    def start(self, when: datetime.datetime) -> None:
        self._state = 'running'
        self._date_work_started = when
        self.get_parent().update_start_date(when)

    def dump(self, indent: str = '', mask_uid: bool = False) -> str:
        return f'{super().dump(indent, mask_uid)}\n' \
               f'{indent}  State: {self._state}\n' \
               f'{indent}  Work started: {self._date_work_started}\n' \
               f'{indent}  Work ended: {self._date_work_ended}'

    def get_incomplete_pomodoros(self) -> Iterable[Pomodoro]:
        for pomodoro in self.values():
            if pomodoro.is_startable():
                yield pomodoro

    def get_tags(self) -> Set[str]:
        res = set[str]()
        for t in TAG_REGEX.finditer(self._name):
            res.add(t.group(1).lower())
        return res

    def get_display_name(self) -> str:
        return textwrap.shorten(self.get_name(), width=60, placeholder='...')

    def get_short_display_name(self) -> str:
        return textwrap.shorten(self.get_name(), width=30, placeholder='...')

    def get_total_elapsed_time(self) -> datetime.timedelta:
        total = sum([p.get_elapsed_work_duration() for p in self.values()])
        return datetime.timedelta(seconds=round(total))

    def is_tracker(self) -> bool:
        for p in self.values():
            if p.get_type() == POMODORO_TYPE_TRACKER:
                return True
        return False

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['date_work_started'] = self._date_work_started
        d['date_work_ended'] = self._date_work_ended
        d['state'] = self._state
        return d

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
from typing import Iterable, Tuple

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem


class Backlog(AbstractDataContainer[Workitem, 'User']):
    """Backlog is a named list of workitems, belonging to a User."""
    _date_work_started: datetime.datetime | None

    def __init__(self,
                 name: str,
                 user: 'User',
                 uid: str,
                 create_date: datetime.datetime):
        super().__init__(name=name, parent=user, uid=uid, create_date=create_date)
        self._date_work_started = None

    def __str__(self):
        return f'Backlog "{self._name}"'

    def get_running_workitem(self) -> Tuple[Workitem, Pomodoro] | Tuple[None, None]:
        for workitem in self.values():
            for pomodoro in workitem.values():
                if pomodoro.is_running():
                    return workitem, pomodoro
        return None, None

    def get_incomplete_workitems(self) -> Iterable[Workitem]:
        for workitem in self.values():
            if not workitem.is_sealed():
                yield workitem

    def is_today(self) -> bool:
        # "Today" = Backlog date corresponds to today's date
        # UC-3: The backlog is marked as "today" if it was created on the same date as today (day, month, year)
        return datetime.date.today() == self.get_create_date().date()

    def get_owner(self) -> 'User':
        return self._parent

    def get_start_date(self) -> datetime.datetime | None:
        return self._date_work_started

    def update_start_date(self, when: datetime.datetime) -> None:
        if self._date_work_started is None or self._date_work_started > when:
            self._date_work_started = when

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['date_work_started'] = self._date_work_started
        return d

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
from typing import Iterable

from fk.core.abstract_data_item import AbstractDataItem
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem


class Backlog(AbstractDataItem):
    """Backlog is a named list of workitems, belonging to a User."""

    _name: str
    _workitems: dict[str, Workitem]
    _owner: 'User'

    def __init__(self,
                 name: str,
                 user: 'User',
                 uid: str,
                 create_date: datetime.datetime):
        super().__init__(uid=uid, parent=user, create_date=create_date)
        self._name = name
        self._workitems = dict()
        self._owner = user

    def __getitem__(self, uid: str) -> Workitem:
        return self._workitems[uid]

    def __contains__(self, uid: str):
        return uid in self._workitems

    def __setitem__(self, uid: str, value: Workitem):
        self._workitems[uid] = value

    def __delitem__(self, uid: str):
        del self._workitems[uid]

    def __iter__(self) -> Iterable[str]:
        return (x for x in self._workitems)

    def __len__(self):
        return len(self._workitems)

    def values(self) -> Iterable[Workitem]:
        # items = list(self._workitems.values())
        # items.sort(key=AbstractDataItem.get_last_modified_date, reverse=True)
        # return items
        return self._workitems.values()

    def __str__(self):
        return f'Backlog "{self._name}"'

    def get_name(self) -> str:
        return self._name

    def set_name(self, new_name: str) -> None:
        self._name = new_name

    def get_running_workitem(self) -> (Workitem, Pomodoro):
        for workitem in self._workitems.values():
            for pomodoro in workitem:
                if pomodoro.is_running():
                    return workitem, pomodoro
        return None, None

    def get_owner(self) -> 'User':
        return self._owner

    def get_parent(self) -> 'User':
        return self._parent

    def is_today(self) -> bool:
        # "Today" = Created within the last 12 hours
        return (datetime.datetime.now(tz=datetime.timezone.utc) - self.get_create_date()).total_seconds() < 3600 * 12

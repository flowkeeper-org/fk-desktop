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
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro


class User(AbstractDataItem):
    _identity: str
    _name: str
    _is_system_user: bool
    _last_pomodoro: Pomodoro
    _backlogs: dict[str, Backlog]

    def __init__(self,
                 identity: str,
                 name: str,
                 create_date: datetime.datetime,
                 is_system_user: bool):
        super().__init__(identity, None, create_date)
        self._identity = identity
        self._backlogs = dict()
        self._last_pomodoro = None
        self._name = name
        self._is_system_user = is_system_user

    def __str__(self):
        return f'User "{self._name} <{self._identity}>"'

    def get_name(self) -> str:
        return self._name

    def get_identity(self) -> str:
        return self._identity

    def is_system_user(self) -> bool:
        return self._is_system_user

    # Returns (state, total remaining). State can be Unknown, Focus, Rest and Idle
    def get_state(self) -> (str, int):
        if self._last_pomodoro is None:
            return "Unknown", 0
        remaining = self._last_pomodoro.remaining_time_in_current_state()
        if self._last_pomodoro.is_running():
            return "Focus", remaining
        elif remaining > 0:
            return "Rest", remaining
        else:
            return "Idle", 0

    def __getitem__(self, uid: str) -> Backlog:
        return self._backlogs[uid]

    def __contains__(self, uid: str):
        return uid in self._backlogs

    def __setitem__(self, uid: str, value: Backlog):
        self._backlogs[uid] = value

    def __delitem__(self, uid: str):
        del self._backlogs[uid]

    def __iter__(self) -> Iterable[str]:
        return (x for x in self._backlogs)

    def __len__(self):
        return len(self._backlogs)

    def values(self) -> Iterable[Backlog]:
        # items = list(self._backlogs.values())
        # items.sort(key=AbstractDataItem.get_last_modified_date, reverse=True)
        # return items
        return self._backlogs.values()

    def get_parent(self) -> None:
        return None

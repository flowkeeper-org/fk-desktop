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
import uuid
from abc import ABC
from typing import Self, Iterable


def generate_uid() -> str:
    return str(uuid.uuid4())


def generate_unique_name(prefix: str, names: Iterable) -> str:
    check = prefix
    n = 1
    while check in names:
        check = f"{prefix} {n}"
        n += 1
    return check


class AbstractDataItem(ABC):
    _uid: str
    _parent: Self
    _create_date: datetime.datetime
    _last_modified_date: datetime.datetime

    def __init__(self,
                 uid: str,
                 parent: Self | None,
                 create_date: datetime.datetime):
        self._uid = uid
        self._parent = parent
        self._create_date = create_date
        self._last_modified_date = create_date

    def get_uid(self) -> str:
        return self._uid

    # Default implementation delegates to the parent
    def get_owner(self) -> 'User':
        return self._parent.get_owner() if self._parent is not None else None

    def get_parent(self) -> Self:
        return self._parent

    def get_create_date(self) -> datetime.datetime:
        return self._create_date

    def get_last_modified_date(self) -> datetime.datetime:
        return self._last_modified_date

    # Call this every time something changes
    def item_updated(self, date: datetime.datetime = None):
        if date is None:
            date = datetime.datetime.now(datetime.timezone.utc)
        self._last_modified_date = date
        if self._parent is not None:
            self._parent.item_updated(date)

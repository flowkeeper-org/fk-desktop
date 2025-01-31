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
from typing import Iterable, TypeVar, Generic


def generate_uid() -> str:
    return str(uuid.uuid4())


def generate_unique_name(prefix: str, names: Iterable) -> str:
    # UC-3: An incremental index is appended to the new backlog / WI name, if there's an existing duplicate
    check = prefix
    n = 1
    while check in names:
        check = f"{prefix} {n}"
        n += 1
    return check


TParent = TypeVar('TParent', bound='AbstractDataItem')


class AbstractDataItem(ABC, Generic[TParent]):
    _uid: str
    _parent: TParent | None
    _create_date: datetime.datetime
    _last_modified_date: datetime.datetime

    def __init__(self,
                 uid: str,
                 parent: TParent | None,
                 create_date: datetime.datetime):
        self._uid = uid
        self._parent = parent
        self._create_date = create_date
        self._last_modified_date = create_date

    def get_uid(self) -> str:
        return self._uid

    # Default implementation delegates to the parent
    def get_owner(self) -> 'User':
        # UC-3: All data objects are owned by a User, or delegated to their parent
        return self._parent.get_owner() if self._parent is not None else None

    def get_parent(self) -> TParent:
        return self._parent

    def dump(self, indent: str = '', mask_uid: bool = False) -> str:
        owner = self.get_owner()
        owner_name = owner.get_uid() if owner is not None else 'N/A'
        parent_uid = self._parent.get_uid() if self._parent is not None else 'N/A'
        return f'{indent}- Class: {self.__class__.__name__}\n' \
               f'{indent}  UID: {"<MASKED>" if mask_uid else self._uid}\n' \
               f'{indent}  Owner: {owner_name}\n' \
               f'{indent}  Parent UID: {parent_uid}\n' \
               f'{indent}  Create date: {self._create_date}\n' \
               f'{indent}  Last modified: {self._last_modified_date}'

    def get_create_date(self) -> datetime.datetime:
        return self._create_date

    def get_last_modified_date(self) -> datetime.datetime:
        return self._last_modified_date

    # Call this every time something changes
    def item_updated(self, date: datetime.datetime = None):
        # UC-2: Update timestamps propagate to parents. The latest timestamp is kept, they can't decrease.
        if date is None:
            date = datetime.datetime.now(datetime.timezone.utc)
        # Some actions may happen retroactively, e.g. a Pomodoro might be auto-sealed "in the past"
        if self._last_modified_date is None or self._last_modified_date < date:
            self._last_modified_date = date
        if self._parent is not None:
            self._parent.item_updated(date)

    def supports_children(self) -> bool:
        return False

    def change_parent(self, new_parent: TParent) -> None:
        if self._parent is not None and self._parent.supports_children():
            del self._parent[self._uid]
            new_parent[self._uid] = self
        self._parent = new_parent

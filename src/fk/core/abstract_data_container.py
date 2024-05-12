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
from typing import Iterable, Generic, TypeVar

from fk.core.abstract_data_item import AbstractDataItem

TChild = TypeVar('TChild', bound=AbstractDataItem)
TParent = TypeVar('TParent', bound=AbstractDataItem)


class AbstractDataContainer(AbstractDataItem[TParent], Generic[TChild, TParent]):
    _name: str
    _children: dict[str, TChild]

    def __init__(self,
                 name: str,
                 parent: TParent,
                 uid: str,
                 create_date: datetime.datetime):
        super().__init__(uid=uid, parent=parent, create_date=create_date)
        self._name = name
        self._children = dict()

    def __getitem__(self, uid: str) -> TChild:
        return self._children[uid]

    def __contains__(self, uid: str):
        return uid in self._children

    def __setitem__(self, uid: str, value: TChild):
        self._children[uid] = value

    def __delitem__(self, uid: str):
        del self._children[uid]

    def __iter__(self) -> Iterable[str]:
        return (x for x in self._children)

    def __len__(self):
        return len(self._children)

    def values(self) -> Iterable[TChild]:
        return self._children.values()

    def keys(self) -> Iterable[str]:
        return self._children.keys()

    def names(self) -> Iterable[str]:
        return [child.get_name() for child in self._children.values()]

    def get_name(self) -> str:
        return self._name

    def set_name(self, new_name: str) -> None:
        self._name = new_name

    def get(self, key: str, default: TChild = None) -> TChild:
        if key in self._children:
            return self._children[key]
        else:
            return default

    def dump(self, indent: str = '') -> str:
        if len(self._children) > 0:
            children = f'\n{indent} --------\n'.join(child.dump(indent + ' - ') for child in self._children.values())
        else:
            children = f'{indent} - <None>'
        return f'{super().dump(indent)}\n' \
               f'{indent} - Name: {self._name}\n' \
               f'{indent} - Children: {len(self._children)}\n' \
               f'{children}'

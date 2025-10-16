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
    _children_with_order: list[TChild]

    def __init__(self,
                 name: str,
                 parent: TParent,
                 uid: str,
                 create_date: datetime.datetime):
        super().__init__(uid=uid, parent=parent, create_date=create_date)
        self._name = name
        self._children = dict()
        self._children_with_order = list()

    def __getitem__(self, uid: str) -> TChild:
        return self._children[uid]

    def __contains__(self, uid: str):
        return uid in self._children

    def __setitem__(self, uid: str, value: TChild):
        if uid not in self._children:
            self._children[uid] = value
            self._children_with_order.append(value)

    def __delitem__(self, uid: str):
        old = self._children.get(uid, None)
        del self._children[uid]
        self._children_with_order.remove(old)

    def __iter__(self) -> Iterable[str]:
        for child in self._children_with_order:
            yield child.get_uid()

    def __len__(self):
        return len(self._children_with_order)

    def values(self) -> list[TChild]:
        return self._children_with_order

    def first(self) -> TChild:
        return self._children_with_order[0] if len(self._children_with_order) > 0 else None

    def keys(self) -> Iterable[str]:
        for child in self._children_with_order:
            yield child.get_uid()

    def names(self) -> list[str]:
        return [child.get_name() for child in self.values()]

    def get_name(self) -> str:
        return self._name

    def set_name(self, new_name: str) -> None:
        self._name = new_name

    def move_child(self, child: TChild, index_to: int) -> None:
        index_from = self._children_with_order.index(child)
        self._children_with_order.insert(index_to if index_to <= index_from else index_to - 1,
                                         self._children_with_order.pop(index_from))

    def get(self, key: str, default: TChild = None) -> TChild:
        if key in self._children:
            return self._children[key]
        else:
            return default

    def supports_children(self) -> bool:
        return True

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        if len(self) > 0:
            children = f'\n'.join(child.dump(indent + '  ', mask_uid, mask_last_modified) for child in self.values())
        else:
            children = f'{indent}  - <Empty>'
        return f'{super().dump(indent, mask_uid, mask_last_modified)}\n' \
               f'{indent}  Name: {self._name}\n' \
               f'{indent}  Children:\n' \
               f'{children}'

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['name'] = self._name
        return d

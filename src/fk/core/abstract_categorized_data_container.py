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
from typing import Generic, TypeVar

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_data_item import AbstractDataItem
from fk.core.category import Category

TChild = TypeVar('TChild', bound=AbstractDataItem)
TParent = TypeVar('TParent', bound=AbstractDataItem)


class AbstractCategorizedDataContainer(AbstractDataContainer[TChild, TParent], Generic[TChild, TParent]):
    _categories: set[Category]

    def __init__(self,
                 name: str,
                 parent: TParent,
                 uid: str,
                 create_date: datetime.datetime,
                 initial_categories: set[Category]):
        super().__init__(name=name, parent=parent, uid=uid, create_date=create_date)
        self._categories = initial_categories

    def get_categories(self) -> set[Category]:
        return self._categories

    def has_category(self, category: Category) -> bool:
        return category in self._categories

    def set_categories(self, categories: set[Category]) -> None:
        self._categories = categories

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        if len(self._categories) > 0:
            cats = f'\n'.join(cat.dump(indent + '  ', mask_uid, mask_last_modified) for cat in self._categories)
        else:
            cats = f'{indent}  - <Empty>'
        return f'{super().dump(indent, mask_uid, mask_last_modified)}\n' \
               f'{indent}  Categories:\n' \
               f'{cats}'

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['categories'] = self._categories
        return d

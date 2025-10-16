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
from typing import Callable

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.category import Category
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant
from fk.core.user import User


def parse_categories(param: str) -> set[str]:
    if param:
        return set(param.split(';'))
    return set()


def resolve_categories(param: str, user: User) -> set[Category]:
    return set([user.find_category_by_id(s, raise_if_not_found=True) for s in parse_categories(param)])


# CreateCategory("123-456-789", "234-567-890", "Important")
@strategy
class CreateCategoryStrategy(AbstractStrategy[Tenant]):
    _category_uid: str
    _parent_uid: str
    _category_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._category_uid = params[0]
        self._parent_uid = params[1]
        self._category_name = params[2]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        parent_category = user.find_category_by_id(self._parent_uid)
        if parent_category is None:
            raise Exception(f'Parent category "{self._parent_uid}" does not exist')

        child_category = user.find_category_by_id(self._category_uid)
        if child_category is not None:
            raise Exception(f'Child category "{self._category_uid}" already exists')

        emit(events.BeforeCategoryCreate, {
            'category_name': self._category_name,
            'parent_category': parent_category,
            'category_uid': self._category_uid,
        }, self._carry)
        category = Category(self._category_name, self._category_uid, False, parent_category, self._when)
        parent_category[self._category_uid] = category
        category.item_updated(self._when)    # This will also update parent Category and User
        print('Emitting')
        emit(events.AfterCategoryCreate, {
            'category': category
        }, self._carry)


# DeleteCategory("123-456-789", "")
@strategy
class DeleteCategoryStrategy(AbstractStrategy[Tenant]):
    _category_uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._category_uid = params[0]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        category = user.find_category_by_id(self._category_uid)
        if category is None:
            raise Exception(f'Category "{self._category_uid}" not found')

        if category.is_root() is None:
            raise Exception(f'Cannot delete root category')

        params = {
            'category': category
        }
        emit(events.BeforeCategoryDelete, params, self._carry)

        # Delete all child categories recursively
        for child in list(category.values()):
            self.execute_another(emit,
                                 data,
                                 DeleteCategoryStrategy,
                                 [child.get_uid()])
        category.item_updated(self._when)    # This will also update parent Category and User

        # Now we can delete the category itself
        del category.get_parent()[self._category_uid]

        emit(events.AfterCategoryDelete, params, self._carry)


# RenameCategory("123-456-789", "New name")
@strategy
class RenameCategoryStrategy(AbstractStrategy[Tenant]):
    _category_uid: str
    _category_new_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._category_uid = params[0]
        self._category_new_name = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        category = user.find_category_by_id(self._category_uid)
        if category is None:
            raise Exception(f'Category "{self._category_uid}" not found')
        if category.is_root():
            raise Exception(f'Cannot rename root category')

        if self._category_new_name == category.get_name():
            # Nothing to do here
            return

        params = {
            'category': category,
            'old_name': category.get_name(),
            'new_name': self._category_new_name,
        }
        emit(events.BeforeCategoryRename, params, self._carry)
        category.set_name(self._category_new_name)
        category.item_updated(self._when)
        emit(events.AfterCategoryRename, params, self._carry)


# ReorderCategory("123-456-789", "0")
@strategy
class ReorderCategoryStrategy(AbstractStrategy[Tenant]):
    _category_uid: str
    _new_index: int

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._category_uid = params[0]
        self._new_index = int(params[1])

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        category: Category = user.find_category_by_id(self._category_uid)
        if category is None:
            raise Exception(f'Category "{self._category_uid}" not found')
        if category.is_root():
            raise Exception(f'Cannot reorder root category')

        params = {
            'category': category,
            'new_index': self._new_index,
        }
        emit(events.BeforeCategoryReorder, params, self._carry)
        category.get_parent().move_child(category, self._new_index)
        category.item_updated(self._when)
        emit(events.AfterCategoryReorder, params, self._carry)

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
from fk.core.backlog import Backlog
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem_strategies import DeleteWorkitemStrategy


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
        # UC-2: An exception is raised if we try to create a User, Backlog or Workitem with a duplicate UID within its direct parent
        if self._backlog_uid in user:
            raise Exception(f'Backlog "{self._backlog_uid}" already exists')

        emit(events.BeforeBacklogCreate, {
            'backlog_name': self._backlog_name,
            'backlog_owner': user,
            'backlog_uid': self._backlog_uid,
        }, self._carry)
        backlog = Backlog(self._backlog_name, user, self._backlog_uid, self._when)
        user[self._backlog_uid] = backlog
        backlog.item_updated(self._when)    # This will also update the User
        emit(events.AfterBacklogCreate, {
            'backlog': backlog
        }, self._carry)


# DeleteCategory("123-456-789", "")
@strategy
class DeleteCategoryStrategy(AbstractStrategy[Tenant]):
    _backlog_uid: str

    def get_backlog_uid(self) -> str:
        return self._backlog_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._backlog_uid = params[0]

    def requires_sealing(self) -> bool:
        return True

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        # UC-2: Trying to delete a User, Backlog or Workitem by ID which doesn't exist in its direct parent, will throw an exception
        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = user[self._backlog_uid]

        params = {
            'backlog': backlog
        }
        emit(events.BeforeBacklogDelete, params, self._carry)

        # UC-1: Deleting a backlog will first delete all children workitems recursively
        # First delete all workitems recursively
        for workitem in list(backlog.values()):
            self.execute_another(emit,
                                 data,
                                 DeleteWorkitemStrategy,
                                 [workitem.get_uid()])
        backlog.item_updated(self._when)    # This will also update the User

        # Now we can delete the backlog itself
        del user[self._backlog_uid]

        # UC-3: The strategies which do something recursively, wrap inner logic in the Before/After events
        emit(events.AfterBacklogDelete, params, self._carry)


# RenameCategory("123-456-789", "New name")
@strategy
class RenameCategoryStrategy(AbstractStrategy[Tenant]):
    _backlog_uid: str
    _backlog_new_name: str

    def get_backlog_uid(self) -> str:
        return self._backlog_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._backlog_uid = params[0]
        self._backlog_new_name = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]
        # UC-2: Trying to rename a User, Backlog or Workitem by ID which doesn't exist in its direct parent, will throw an exception
        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = user[self._backlog_uid]

        params = {
            'backlog': backlog,
            'old_name': backlog.get_name(),
            'new_name': self._backlog_new_name,
        }
        emit(events.BeforeBacklogRename, params, self._carry)
        backlog.set_name(self._backlog_new_name)
        backlog.item_updated(self._when)
        emit(events.AfterBacklogRename, params, self._carry)

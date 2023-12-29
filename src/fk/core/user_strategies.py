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
from fk.core.backlog_strategies import DeleteBacklogStrategy
from fk.core.strategy_factory import strategy
from fk.core.user import User


# CreateUser("alice@example.com", "Alice Cooper")
@strategy
class CreateUserStrategy(AbstractStrategy['App']):
    _user_identity: str
    _user_name: str

    def get_user_identity(self) -> str:
        return self._user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'App',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._user_identity = params[0]
        self._user_name = params[1]

    def execute(self) -> (str, any):
        if not self._user.is_system_user():
            raise Exception(f'A non-System user "{self._user}" tries to create user "{self._user_identity}"')
        if self._user_identity in self._data:
            raise Exception(f'User "{self._user_identity}" already exists')
        self._emit(events.BeforeUserCreate, {
            'user_identity': self._user_identity,
            'user_name': self._user_name,
        })
        user = User(self._data, self._user_identity, self._user_name, self._when, False)
        self._data[self._user_identity] = user
        user.item_updated(self._when)   # This is not strictly required, but just in case we will create Teams
        self._emit(events.AfterUserCreate, {
            'user': user
        })
        return None, None


# DeleteUser("alice@example.com", "")
@strategy
class DeleteUserStrategy(AbstractStrategy['App']):
    _user_identity: str

    def get_user_identity(self) -> str:
        return self._user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'App',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._user_identity = params[0]

    def execute(self) -> (str, any):
        if self._user_identity not in self._data:
            raise Exception(f'User "{self._user_identity}" not found')
        if self._data[self._user_identity].is_system_user():
            raise Exception(f'Not allowed to delete System user')
        if not self._user.is_system_user():
            raise Exception(f'A non-System user "{self._user}" tries to delete user "{self._user_identity}"')

        user = self._data[self._user_identity]
        params = {
            'user': user
        }
        self._emit(events.BeforeUserDelete, params)

        # Cascade delete all backlogs first
        for backlog in user.values():
            self.execute_another(DeleteBacklogStrategy, [backlog.get_uid()])
        user.item_updated(self._when)

        # Now delete the user
        del self._data[self._user_identity]
        self._emit(events.AfterUserDelete, params)
        return None, None


# RenameUser("alice@example.com", "Alice Cooper")
@strategy
class RenameUserStrategy(AbstractStrategy['App']):
    _user_identity: str
    _new_user_name: str

    def get_user_identity(self) -> str:
        return self._user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'App',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._user_identity = params[0]
        self._new_user_name = params[1]

    def execute(self) -> (str, any):
        if self._user_identity not in self._data:
            raise Exception(f'User "{self._user_identity}" not found')
        if self._data[self._user_identity].is_system_user():
            raise Exception(f'Not allowed to rename System user')
        if not self._user.is_system_user():
            raise Exception(f'A non-System user "{self._user}" tries to rename user "{self._user_identity}"')

        user = self._data[self._user_identity]
        old_name = user.get_name()
        params = {
            'user': user,
            'old_name': old_name,
            'new_name': self._new_user_name,
        }
        self._emit(events.BeforeUserRename, params)
        user._name = self._new_user_name
        user.item_updated(self._when)
        self._emit(events.AfterUserRename, params)
        return None, None

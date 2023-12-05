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
from fk.core.user import User


# CreateUser("alice@example.com", "Alice Cooper")
class CreateUserStrategy(AbstractStrategy):
    _user_identity: str
    _user_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], any],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._user_identity = params[0]
        self._user_name = params[1]

    def get_name(self) -> str:
        return 'CreateUser'

    def execute(self) -> (str, any):
        if not self._who.is_system_user():
            raise Exception(f'A non-System user "{self._who}" tries to create user "{self._user_identity}"')
        if self._user_identity in self._users:
            raise Exception(f'User "{self._user_identity}" already exists')
        self._emit(events.BeforeUserCreate, {
            'user_identity': self._user_identity,
            'user_name': self._user_name,
        })
        user = User(self._user_identity, self._user_name, self._when, False)
        self._users[self._user_identity] = user
        user.item_updated(self._when)   # This is not strictly required, but just in case we will create Teams
        self._emit(events.AfterUserCreate, {
            'user': user
        })
        return None, None


# DeleteUser("alice@example.com", "")
class DeleteUserStrategy(AbstractStrategy):
    _user_identity: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], any],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._user_identity = params[0]

    def get_name(self) -> str:
        return 'DeleteUser'

    def execute(self) -> (str, any):
        if self._user_identity not in self._users:
            raise Exception(f'User "{self._user_identity}" not found')
        if self._users[self._user_identity].is_system_user():
            raise Exception(f'Not allowed to delete System user')
        if not self._who.is_system_user():
            raise Exception(f'A non-System user "{self._who}" tries to delete user "{self._user_identity}"')

        user = self._users[self._user_identity]
        params = {
            'user': user
        }
        self._emit(events.BeforeUserDelete, params)

        # Cascade delete all backlogs first
        for backlog in user.values():
            self.execute_another(DeleteBacklogStrategy, [backlog.get_uid()])
        user.item_updated(self._when)

        # Now delete the user
        del self._users[self._user_identity]
        self._emit(events.AfterUserDelete, params)
        return None, None


# RenameUser("alice@example.com", "Alice Cooper")
class RenameUserStrategy(AbstractStrategy):
    _user_identity: str
    _new_user_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], any],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._user_identity = params[0]
        self._new_user_name = params[1]

    def get_name(self) -> str:
        return 'RenameUser'

    def execute(self) -> (str, any):
        if self._user_identity not in self._users:
            raise Exception(f'User "{self._user_identity}" not found')
        if self._users[self._user_identity].is_system_user():
            raise Exception(f'Not allowed to rename System user')
        if not self._who.is_system_user():
            raise Exception(f'A non-System user "{self._who}" tries to rename user "{self._user_identity}"')

        user = self._users[self._user_identity]
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

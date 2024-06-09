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
from fk.core.tenant import Tenant
from fk.core.user import User


def is_system_user(user_identity: str):
    return user_identity == 'admin@local.host'


# CreateUser("alice@example.com", "Alice Cooper")
@strategy
class CreateUserStrategy(AbstractStrategy[Tenant]):
    _target_user_identity: str
    _user_name: str

    def get_target_user_identity(self) -> str:
        return self._target_user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._target_user_identity = params[0]
        self._user_name = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        if not is_system_user(self._user_identity):
            raise Exception(f'A non-System user "{self._user_identity}" tries to create user "{self._user_identity}"')
        if self._target_user_identity in data:
            raise Exception(f'User "{self._target_user_identity}" already exists')
        emit(events.BeforeUserCreate, {
            'user_identity': self._target_user_identity,
            'user_name': self._user_name,
        }, self._carry)
        user = User(data, self._target_user_identity, self._user_name, self._when, False)
        data[self._target_user_identity] = user
        user.item_updated(self._when)   # This will also update the Tenant
        emit(events.AfterUserCreate, {
            'user': user
        }, self._carry)
        return None, None


# DeleteUser("alice@example.com", "")
@strategy
class DeleteUserStrategy(AbstractStrategy[Tenant]):
    _target_user_identity: str

    def get_target_user_identity(self) -> str:
        return self._target_user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._target_user_identity = params[0]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        if self._target_user_identity not in data:
            raise Exception(f'User "{self._target_user_identity}" not found')
        if data[self._target_user_identity].is_system_user():
            raise Exception(f'Not allowed to delete System user')
        if not is_system_user(self._user_identity):
            raise Exception(f'A non-System user "{self._user_identity}" '
                            f'tries to delete user "{self._target_user_identity}"')

        user: User = data[self._target_user_identity]
        params = {
            'user': user
        }
        emit(events.BeforeUserDelete, params, self._carry)

        # Cascade delete all backlogs first
        for backlog in user.values():
            self.execute_another(emit, data, DeleteBacklogStrategy, [backlog.get_uid()])
        user.item_updated(self._when)

        # Now delete the user
        del data[self._target_user_identity]
        emit(events.AfterUserDelete, params, self._carry)
        return None, None


# RenameUser("alice@example.com", "Alice Cooper")
@strategy
class RenameUserStrategy(AbstractStrategy[Tenant]):
    _target_user_identity: str
    _new_user_name: str

    def get_target_user_identity(self) -> str:
        return self._target_user_identity

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._target_user_identity = params[0]
        self._new_user_name = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        if self._target_user_identity not in data:
            raise Exception(f'User "{self._target_user_identity}" not found')
        if data[self._target_user_identity].is_system_user():
            raise Exception(f'Not allowed to rename System user')
        if not is_system_user(self._user_identity):
            raise Exception(f'A non-System user "{self._user_identity}" '
                            f'tries to rename user "{self._target_user_identity}"')

        user: User = data[self._target_user_identity]
        old_name = user.get_name()
        params = {
            'user': user,
            'old_name': old_name,
            'new_name': self._new_user_name,
        }
        emit(events.BeforeUserRename, params, self._carry)
        user._name = self._new_user_name
        user.item_updated(self._when)
        emit(events.AfterUserRename, params, self._carry)
        return None, None

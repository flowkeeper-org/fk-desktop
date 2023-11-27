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
from fk.core.workitem_strategies import DeleteWorkitemStrategy


# CreateBacklog("123-456-789", "The first backlog")
class CreateBacklogStrategy(AbstractStrategy):
    _backlog_uid: str
    _backlog_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._backlog_uid = params[0]
        self._backlog_name = params[1]

    def get_name(self) -> str:
        return 'CreateBacklog'

    def execute(self) -> (str, any):
        if self._backlog_uid in self._who:
            raise Exception(f'Backlog "{self._backlog_uid}" already exists')

        self._emit(events.BeforeBacklogCreate, {
            'backlog_name': self._backlog_name,
            'backlog_owner': self._who,
            'backlog_uid': self._backlog_uid,
        })
        backlog = Backlog(self._backlog_name, self._who, self._backlog_uid, self._when)
        self._who[self._backlog_uid] = backlog
        backlog.item_updated(self._when)    # This will update the User
        self._emit(events.AfterBacklogCreate, {
            'backlog': backlog
        })
        return None, None


# DeleteBacklog("123-456-789", "")
class DeleteBacklogStrategy(AbstractStrategy):
    _backlog_uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._backlog_uid = params[0]

    def get_name(self) -> str:
        return 'DeleteBacklog'

    def execute(self) -> (str, any):
        if self._backlog_uid not in self._who:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = self._who[self._backlog_uid]

        params = {
            'backlog': backlog
        }
        self._emit(events.BeforeBacklogDelete, params)

        # First delete all workitems recursively
        for workitem in list(backlog.values()):
            self.execute_another(DeleteWorkitemStrategy, [
                workitem.get_uid()
            ])
        backlog.item_updated(self._when)    # This will update the User

        # Now we can delete the backlog itself
        del self._who[self._backlog_uid]

        self._emit(events.AfterBacklogDelete, params)
        return None, None


# RenameBacklog("123-456-789", "New name")
class RenameBacklogStrategy(AbstractStrategy):
    _backlog_uid: str
    _backlog_new_name: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 username: str,
                 params: list[str],
                 emit: Callable[[str, dict[str, any]], None],
                 users: dict[str, 'User'],
                 settings: AbstractSettings):
        super().__init__(seq, when, username, params, emit, users, settings)
        self._backlog_uid = params[0]
        self._backlog_new_name = params[1]

    def get_name(self) -> str:
        return 'RenameBacklog'

    def execute(self) -> (str, any):
        if self._backlog_uid not in self._who:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = self._who[self._backlog_uid]

        params = {
            'backlog': backlog,
            'old_name': backlog.get_name(),
            'new_name': self._backlog_new_name,
        }
        self._emit(events.BeforeBacklogRename, params)
        backlog.set_name(self._backlog_new_name)
        backlog.item_updated(self._when)
        self._emit(events.AfterBacklogRename, params)
        return None, None

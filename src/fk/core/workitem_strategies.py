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
from fk.core.pomodoro_strategies import VoidPomodoroStrategy
from fk.core.strategy_factory import strategy
from fk.core.user import User
from fk.core.workitem import Workitem


# CreateWorkitem("123-456-789", "234-567-890", "Wake up")
@strategy
class CreateWorkitemStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _backlog_uid: str
    _workitem_name: str

    def get_backlog_uid(self) -> str:
        return self._backlog_uid

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._workitem_uid = params[0]
        self._backlog_uid = params[1]
        self._workitem_name = params[2]

    def execute(self) -> (str, any):
        user = self._data[self._user.get_identity()]
        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = user[self._backlog_uid]

        if self._workitem_uid in backlog:
            raise Exception(f'Workitem "{self._workitem_uid}" already exists')

        self._emit(events.BeforeWorkitemCreate, {
            'backlog_uid': self._backlog_uid,
            'workitem_uid': self._workitem_uid,
            'workitem_name': self._workitem_name,
        })
        workitem = Workitem(
            self._workitem_name,
            self._workitem_uid,
            backlog,
            self._when,
        )
        backlog[self._workitem_uid] = workitem
        workitem.item_updated(self._when)   # This will also update the Backlog
        self._emit(events.AfterWorkitemCreate, {
            'workitem': workitem,
            'carry': None,
        })
        return None, None


def void_running_pomodoro(strategy: AbstractStrategy, workitem: Workitem) -> None:
    for pomodoro in workitem.values():
        if pomodoro.is_running():
            strategy.execute_another(VoidPomodoroStrategy, [
                workitem.get_uid(),
            ])


# DeleteWorkitem("123-456-789")
@strategy
class DeleteWorkitemStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._workitem_uid = params[0]

    def execute(self) -> (str, any):
        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        void_running_pomodoro(self, workitem)

        params = {
            'workitem': workitem
        }
        self._emit(events.BeforeWorkitemDelete, params)
        workitem.item_updated(self._when)   # Update Backlog
        del workitem.get_parent()[self._workitem_uid]
        self._emit(events.AfterWorkitemDelete, params)
        return None, None


# RenameWorkitem("123-456-789", "Wake up")
@strategy
class RenameWorkitemStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _new_workitem_name: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._workitem_uid = params[0]
        self._new_workitem_name = params[1]

    def execute(self) -> (str, any):
        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if self._new_workitem_name == workitem.get_name():
            # Nothing to do here
            return None, None

        if workitem.is_sealed():
            raise Exception(f'Cannot rename sealed workitem "{self._workitem_uid}"')

        params = {
            'workitem': workitem,
            'old_name': workitem.get_name(),
            'new_name': self._new_workitem_name,
        }
        self._emit(events.BeforeWorkitemRename, params)
        workitem.set_name(self._new_workitem_name)
        workitem.item_updated(self._when)
        self._emit(events.AfterWorkitemRename, params)


# CompleteWorkitem("123-456-789", "canceled")
@strategy
class CompleteWorkitemStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _target_state: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user, params, emit, data, settings, carry)
        self._workitem_uid = params[0]
        self._target_state = params[1]

    def execute(self) -> (str, any):
        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if workitem.is_sealed():
            raise Exception(f'Cannot complete already sealed workitem "{self._workitem_uid}"')

        void_running_pomodoro(self, workitem)

        # Now complete the workitem itself
        params = {
            'workitem': workitem,
            'target_state': self._target_state,
        }
        self._emit(events.BeforeWorkitemComplete, params)
        workitem.seal(self._target_state, self._when)
        workitem.item_updated(self._when)
        self._emit(events.AfterWorkitemComplete, params)
        return None, None

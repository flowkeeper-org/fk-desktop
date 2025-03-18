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
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER, POMODORO_TYPE_COUNTER
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem


# AddPomodoro("123-456-789", "1", ["normal"])
@strategy
class AddPomodoroStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _num_pomodoros: int
    _type: str
    _settings: AbstractSettings

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._num_pomodoros = int(params[1])
        self._type = params[2] if len(params) > 2 else POMODORO_TYPE_NORMAL
        self._settings = settings

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        if self._num_pomodoros < 1:
            raise Exception(f'Cannot add {self._num_pomodoros} pomodoro')

        if self._type not in [POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER, POMODORO_TYPE_COUNTER]:
            raise Exception(f'Unsupported pomodoro type: {self._type}')

        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if workitem.is_sealed():
            raise Exception(f'Workitem "{self._workitem_uid}" is sealed')

        params = {
            'workitem': workitem,
            'num_pomodoros': self._num_pomodoros,
            'pomodoro_type': self._type,
        }
        emit(events.BeforePomodoroAdd, params, self._carry)
        workitem.add_pomodoro(
            self._num_pomodoros,
            float(self._settings.get('Pomodoro.default_work_duration')) if self._type == POMODORO_TYPE_NORMAL else 0,
            float(self._settings.get('Pomodoro.default_rest_duration')) if self._type == POMODORO_TYPE_NORMAL else 0,
            self._type,
            self._when)
        workitem.item_updated(self._when)
        emit(events.AfterPomodoroAdd, params, self._carry)


# RemovePomodoro("123-456-789", "1")
@strategy
class RemovePomodoroStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _num_pomodoros: int

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def requires_sealing(self) -> bool:
        return True

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._num_pomodoros = int(params[1])

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        if self._num_pomodoros < 1:
            raise Exception(f'Cannot remove {self._num_pomodoros} pomodoro')

        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if workitem.is_sealed():
            raise Exception(f'Workitem "{self._workitem_uid}" is sealed')

        # Check that we have enough "new" pomodoro to remove
        to_remove = list[Pomodoro]()
        for p in reversed(workitem.values()):
            if p.is_startable():
                to_remove.append(p)
                if len(to_remove) == self._num_pomodoros:
                    break
        if len(to_remove) < self._num_pomodoros:
            raise Exception(f'Only {len(to_remove)} pomodoro is available, cannot remove {self._num_pomodoros}')

        params = {
            'workitem': workitem,
            'num_pomodoros': self._num_pomodoros,
            'pomodoros': to_remove
        }
        emit(events.BeforePomodoroRemove, params, self._carry)
        for p in to_remove:
            workitem.remove_pomodoro(p)
        workitem.item_updated(self._when)
        emit(events.AfterPomodoroRemove, params, self._carry)


# AddInterruption("123-456-789", "reason", ["123.45"])
@strategy
class AddInterruptionStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _reason: str | None
    _duration: datetime.timedelta | None

    def requires_sealing(self) -> bool:
        return True

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._reason = params[1]
        if len(params) > 2 and params[2]:
            self._duration = datetime.timedelta(seconds=float(params[2]))
        else:
            self._duration = None

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]

        # TODO: Make it timer strategy. Pass timer object into those strategies.
        #  Use timer instead of looking for pomodoros.
        workitem: Workitem | None = None
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if not workitem.has_running_pomodoro():
            raise Exception(f'Workitem "{self._workitem_uid}" is not running')

        for pomodoro in workitem.values():
            if pomodoro.is_running():
                params = {
                    'workitem': workitem,
                    'pomodoro': pomodoro,
                    'reason': self._reason,
                    'duration': self._duration,
                }
                emit(events.BeforePomodoroInterrupted, params, self._carry)
                pomodoro.add_interruption(self._reason, self._duration, False, self._when)
                pomodoro.item_updated(self._when)
                emit(events.AfterPomodoroInterrupted, params, self._carry)
                return

        raise Exception(f'No running pomodoros in "{self._workitem_uid}"')

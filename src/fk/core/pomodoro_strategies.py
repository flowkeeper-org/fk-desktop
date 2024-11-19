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
from fk.core.pomodoro import Pomodoro
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem


# StartWork("123-456-789", "1500", ["300"])
@strategy
class StartWorkStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _work_duration: float
    _rest_duration: float

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
        self._work_duration = float(params[1])
        if len(params) == 3:
            self._rest_duration = float(params[2])
        else:
            self._rest_duration = 0.0

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        user: User = data[self._user_identity]
        if not user.is_local_user():
            # Someone shared their timer state with us -- we won't find a local workitem
            # TODO: Fire some event here
            return None, None

        workitem: Workitem | None = None
        running: Workitem | None = None
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                running, _ = backlog.get_running_workitem()
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if workitem.is_sealed():
            raise Exception(f'Cannot start pomodoro on a sealed workitem "{self._workitem_uid}"')

        if running is not None:
            # This is an unusual case -- instead of throwing an Exception, we tell the
            # calling Source that it should attempt auto-seal and retry.
            return 'auto-seal', running

        for pomodoro in workitem.values():
            if pomodoro.is_startable():
                work_duration = self._work_duration if self._work_duration != 0 else pomodoro.get_work_duration()
                rest_duration = self._rest_duration if self._rest_duration != 0 else pomodoro.get_rest_duration()
                params = {
                    'pomodoro': pomodoro,
                    'workitem': workitem,
                    'work_duration': work_duration,
                    'rest_duration': rest_duration,
                }
                if not workitem.is_running():
                    emit(events.BeforeWorkitemStart, params, self._carry)
                    workitem.start(self._when)
                    emit(events.AfterWorkitemStart, params, self._carry)
                emit(events.BeforePomodoroWorkStart, params, self._carry)
                pomodoro.update_work_duration(work_duration)
                pomodoro.update_rest_duration(rest_duration)
                pomodoro.start_work(self._when)
                pomodoro.item_updated(self._when)
                emit(events.AfterPomodoroWorkStart, params, self._carry)
                return None, None

        raise Exception(f'No startable pomodoro in "{self._workitem_uid}"')

    def encryptable(self) -> bool:
        return self._settings.get('Team.share_state') == 'False'


# Not available externally, not registered as a strategy
# The main difference with StartWork is that we don't start a workitem here and fail if it's not started yet.
class StartRestInternalStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str

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

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if not workitem.is_running():
            raise Exception(f'Cannot start rest on a workitem "{self._workitem_uid}" which is not running')

        # Note that unlike StartWorkStrategy we don't care about auto-sealing here, since this
        # should've been done for the StartWork earlier.
        for pomodoro in workitem.values():
            if pomodoro.is_working():
                params = {
                    'pomodoro': pomodoro,
                    'workitem': workitem,
                    'rest_duration': pomodoro.get_rest_duration(),
                }
                emit(events.BeforePomodoroRestStart, params, self._carry)
                pomodoro.start_rest(self._when)
                pomodoro.item_updated(self._when)
                emit(events.AfterPomodoroRestStart, params, self._carry)
                return None, None

        raise Exception(f'No in-work pomodoro in "{self._workitem_uid}"')


# AddPomodoro("123-456-789", "1")
@strategy
class AddPomodoroStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _num_pomodoros: int

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
        self._default_work_duration = float(settings.get('Pomodoro.default_work_duration'))
        self._default_rest_duration = float(settings.get('Pomodoro.default_rest_duration'))

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        if self._num_pomodoros < 1:
            raise Exception(f'Cannot add {self._num_pomodoros} pomodoro')

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
        }
        emit(events.BeforePomodoroAdd, params, self._carry)
        workitem.add_pomodoro(
            self._num_pomodoros,
            self._default_work_duration,
            self._default_rest_duration,
            self._when)
        workitem.item_updated(self._when)
        emit(events.AfterPomodoroAdd, params, self._carry)
        return None, None


def _complete_pomodoro(user: User,
                       workitem_uid: str,
                       target_state: str,
                       emit: Callable[[str, dict[str, any], any], None],
                       carry: any,
                       when: datetime.datetime) -> None:
    workitem: Workitem | None = None
    for backlog in user.values():
        if workitem_uid in backlog:
            workitem = backlog[workitem_uid]
            break

    if workitem is None:
        raise Exception(f'Workitem "{workitem_uid}" not found')

    if not workitem.is_running():
        raise Exception(f'Workitem "{workitem_uid}" is not running')

    for pomodoro in workitem.values():
        # TODO: Check that if we are finishing work successfully, then the time since the rest started
        #  corresponds well to what was planned, +/- 10 seconds
        if pomodoro.is_running():
            params = {
                'workitem': workitem,
                'pomodoro': pomodoro,
                'target_state': target_state,
            }
            emit(events.BeforePomodoroComplete, params, carry)
            pomodoro.seal(target_state, when)
            pomodoro.item_updated(when)
            emit(events.AfterPomodoroComplete, params, carry)
            return

    raise Exception(f'No running pomodoros in "{workitem_uid}"')


# VoidPomodoro("123-456-789")
@strategy
class VoidPomodoroStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str

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

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        user: User = data[self._user_identity]
        if not user.is_local_user():
            # Someone shared their timer state with us -- we won't find a local workitem
            # TODO: Fire some event here
            return None, None

        _complete_pomodoro(user, self._workitem_uid, 'canceled', emit, self._carry, self._when)
        return None, None

    def encryptable(self) -> bool:
        return self._settings.get('Team.share_state') == 'False'


# Not available externally, not registered as a strategy
class FinishPomodoroInternalStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        user: User = data[self._user_identity]
        _complete_pomodoro(user, self._workitem_uid, 'finished', emit, self._carry, self._when)
        return None, None


# RemovePomodoro("123-456-789", "1")
@strategy
class RemovePomodoroStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _num_pomodoros: int

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

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
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
        return None, None

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
from fk.core.user import User
from fk.core.workitem import Workitem


# StartWork("123-456-789", "1500")
@strategy
class StartWorkStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _work_duration: int

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
        self._work_duration = int(params[1])

    def execute(self) -> (str, any):
        workitem: Workitem | None = None
        running: Workitem | None = None
        user = self._data[self._user.get_identity()]
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
                params = {
                    'pomodoro': pomodoro,
                    'workitem': workitem,
                    'work_duration': work_duration,
                }
                if not workitem.is_running():
                    self._emit(events.BeforeWorkitemStart, params)
                    workitem.start(self._when)
                    workitem.item_updated(self._when)
                    self._emit(events.AfterWorkitemStart, params)
                self._emit(events.BeforePomodoroWorkStart, params)
                pomodoro.update_work_duration(work_duration)
                pomodoro.start_work(self._when)
                pomodoro.item_updated(self._when)
                self._emit(events.AfterPomodoroWorkStart, params)
                return None, None

        raise Exception(f'No startable pomodoro in "{self._workitem_uid}"')


# StartRest("123-456-789", "300")
# The main difference with StartWork is that we don't start a workitem here and fail if it's not started yet.
@strategy
class StartRestStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _rest_duration: int

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
        self._rest_duration = int(params[1])

    def execute(self) -> (str, any):
        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
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
                rest_duration = self._rest_duration if self._rest_duration != 0 else pomodoro.get_rest_duration()
                params = {
                    'pomodoro': pomodoro,
                    'workitem': workitem,
                    'rest_duration': rest_duration,
                }
                self._emit(events.BeforePomodoroRestStart, params)
                pomodoro.update_rest_duration(rest_duration)
                pomodoro.start_rest(self._when)
                pomodoro.item_updated(self._when)
                self._emit(events.AfterPomodoroRestStart, params)
                return None, None

        raise Exception(f'No in-work pomodoro in "{self._workitem_uid}"')


# AddPomodoro("123-456-789", "1")
@strategy
class AddPomodoroStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _num_pomodoros: int

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
        self._num_pomodoros = int(params[1])
        self._default_work_duration = int(settings.get('Pomodoro.default_work_duration'))
        self._default_rest_duration = int(settings.get('Pomodoro.default_rest_duration'))

    def execute(self) -> (str, any):
        if self._num_pomodoros < 1:
            raise Exception(f'Cannot add {self._num_pomodoros} pomodoro')

        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
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
        self._emit(events.BeforePomodoroAdd, params)
        workitem.add_pomodoro(
            self._num_pomodoros,
            self._default_work_duration,
            self._default_rest_duration,
            self._when)
        workitem.item_updated(self._when)
        self._emit(events.AfterPomodoroAdd, params)
        return None, None


# VoidPomodoro("123-456-789")
@strategy
class VoidPomodoroStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str

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

        if not workitem.is_running():
            raise Exception(f'Workitem "{self._workitem_uid}" is not running')

        for pomodoro in workitem.values():
            # TODO: Check that if we are finishing work successfully, then the time since the rest started
            #  corresponds well to what was planned, +/- 10 seconds
            if pomodoro.is_running():
                params = {
                    'workitem': workitem,
                    'pomodoro': pomodoro,
                    'target_state': 'canceled',
                }
                self._emit(events.BeforePomodoroComplete, params)
                pomodoro.seal(self._target_state, self._when)
                pomodoro.item_updated(self._when)
                self._emit(events.AfterPomodoroComplete, params)
                return None, None

        raise Exception(f'No running pomodoros in "{self._workitem_uid}"')


# CompletePomodoro("123-456-789", "finished")
# Legacy
@strategy
class CompletePomodoroStrategy(AbstractStrategy['Tenant']):
    _another: VoidPomodoroStrategy | None

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user: User,
                 params: list[str],
                 emit: Callable[[str, dict[str, any], any], None],
                 data: 'Tenant',
                 settings: AbstractSettings,
                 carry: any = None):
        if params[1] == 'canceled':
            self._another = VoidPomodoroStrategy(seq, when, user, [params[0]], emit, data, settings, carry)
        else:
            self._another = None

    def execute(self) -> (str, any):
        if self._another:
            return self._another.execute()
        else:
            return None, None   # Since version 1.3.x we always complete pomodoros implicitly

# RemovePomodoro("123-456-789", "1")
@strategy
class RemovePomodoroStrategy(AbstractStrategy['Tenant']):
    _workitem_uid: str
    _num_pomodoros: int

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
        self._num_pomodoros = int(params[1])

    def execute(self) -> (str, any):
        if self._num_pomodoros < 1:
            raise Exception(f'Cannot remove {self._num_pomodoros} pomodoro')

        workitem: Workitem | None = None
        user = self._data[self._user.get_identity()]
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
        self._emit(events.BeforePomodoroRemove, params)
        for p in to_remove:
            workitem.remove_pomodoro(p)
        workitem.item_updated(self._when)
        self._emit(events.AfterPomodoroRemove, params)
        return None, None

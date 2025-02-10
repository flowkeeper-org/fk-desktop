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


# StartTimer("123-456-789", "1500", ["300"])
@strategy
class StartTimerStrategy(AbstractStrategy[Tenant]):
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
        workitem: Workitem | None = None
        running: Workitem | None = None
        user: User = data[self._user_identity]
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
                params = {
                    'pomodoro': pomodoro,
                    'workitem': workitem,
                    'work_duration': self._work_duration,
                    'rest_duration': self._rest_duration,
                }
                if not workitem.is_running():
                    emit(events.BeforeWorkitemStart, params, self._carry)
                    workitem.start(self._when)
                    emit(events.AfterWorkitemStart, params, self._carry)
                emit(events.BeforePomodoroWorkStart, params, self._carry)
                if self._work_duration != 0:
                    pomodoro.update_work_duration(self._work_duration)
                if self._rest_duration != 0:
                    pomodoro.update_rest_duration(self._rest_duration)
                pomodoro.start_work(self._when)
                pomodoro.item_updated(self._when)
                emit(events.AfterPomodoroWorkStart, params, self._carry)
                return None, None

        raise Exception(f'No startable pomodoro in "{self._workitem_uid}"')


# StopTimer("")
# This strategy assumes an explicit stop by the end user. Timer stops are implied and do not produce this strategy.
@strategy
class StopTimerStrategy(AbstractStrategy[Tenant]):
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for b in user.values():
            for w in b.values():
                if w.has_running_pomodoro():
                    workitem = w
                    break

        if workitem is None:
            # TODO: Use the real Timer object
            raise Exception(f'Cannot stop the timer -- no running workitems')

        pomodoro = workitem.get_running_pomodoro()

        if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
            # Stopping a normal running pomodoro means voiding it
            params = {
                'workitem': workitem,
                'pomodoro': pomodoro,
                'reason': 'Voided automatically because you completed the workitem while the timer was running.',
            }
            emit(events.BeforePomodoroVoided, params, self._carry)
            pomodoro.void(self._when)
            emit(events.AfterPomodoroVoided, params, self._carry)
        elif pomodoro.get_type() == POMODORO_TYPE_TRACKER:
            params = {
                'workitem': workitem,
                'pomodoro': pomodoro,
            }
            emit(events.BeforePomodoroComplete, params, self._carry)
            pomodoro.seal(self._when)
            pomodoro.item_updated(self._when)
            emit(events.AfterPomodoroComplete, params, self._carry)
        else:
            raise Exception(f'Cannot stop the timer for a running pomodoro of type {pomodoro.get_type()}')

        return None, None


class TimerRingInternalStrategy(AbstractStrategy[Tenant]):
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        # TODO: Check the timer state and decide what to do. Execute the corresponding strategy as a result
        #  and emit timer events. The Timer and its UI, both of which subscribe to those events, will decide
        #  what to do next. For example, the Timer might schedule rest after work has been finished.
        return None, None


# StartWork("123-456-789", "1500", ["300"])
# DEPRECATED
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
        self.execute_another(emit,
                             data,
                             StartTimerStrategy,
                             [self._workitem_uid, self._work_duration, self._rest_duration])
        return None, None


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

        if not workitem.has_running_pomodoro():
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


def _complete_pomodoro(user: User,
                       workitem_uid: str,
                       emit: Callable[[str, dict[str, any], any], None],
                       carry: any,
                       when: datetime.datetime,
                       tracker_only: bool = False) -> None:
    workitem: Workitem | None = None
    for backlog in user.values():
        if workitem_uid in backlog:
            workitem = backlog[workitem_uid]
            break

    if workitem is None:
        raise Exception(f'Workitem "{workitem_uid}" not found')

    if not workitem.has_running_pomodoro():
        raise Exception(f'Workitem "{workitem_uid}" is not running')

    if tracker_only:
        for pomodoro in workitem.values():
            if pomodoro.get_type() != POMODORO_TYPE_TRACKER:
                raise Exception(f'Trying to finish tracking time on a workitem "{workitem_uid}" which has non-tracker pomodoros of type {pomodoro.get_type()}')

    for pomodoro in workitem.values():
        # TODO: Check that if we are finishing work successfully, then the time since the rest started
        #  corresponds well to what was planned, +/- 10 seconds
        if pomodoro.is_running():
            params = {
                'workitem': workitem,
                'pomodoro': pomodoro,
            }
            emit(events.BeforePomodoroComplete, params, carry)
            pomodoro.seal(when)
            pomodoro.item_updated(when)
            emit(events.AfterPomodoroComplete, params, carry)
            return

    raise Exception(f'No running pomodoros in "{workitem_uid}"')


# VoidPomodoro("123-456-789")
# DEPRECATED
@strategy
class VoidPomodoroStrategy(AbstractStrategy[Tenant]):
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        self.execute_another(emit,
                             data,
                             StopTimerStrategy,
                             [])
        return None, None


# Not available externally, not registered as a strategy
class FinishPomodoroInternalStrategy(AbstractStrategy[Tenant]):
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
        _complete_pomodoro(user, self._workitem_uid, emit, self._carry, self._when)
        return None, None


# FinishTracking("123-456-789")
# DEPRECATED
@strategy
class FinishTrackingStrategy(AbstractStrategy[Tenant]):
    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        self.execute_another(emit,
                             data,
                             StopTimerStrategy,
                             [])
        return None, None

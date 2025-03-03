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
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER
from fk.core.strategy_factory import strategy
from fk.core.tenant import Tenant
from fk.core.timer_data import TimerData
from fk.core.workitem import Workitem


# StartTimer("123-456-789", ["1500", ["300"]])
@strategy
class StartTimerStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _work_duration: float
    _rest_duration: float

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
        if len(params) >= 2 and params[1] != '':
            self._work_duration = float(params[1])
            if len(params) >= 3 and params[2] != '':
                self._rest_duration = float(params[2])
            else:
                self._rest_duration = 0.0  # There will be a long break
        else:
            self._work_duration = 0.0  # This will be a tracker
            self._rest_duration = 0.0

    def get_workitem(self,
                     data: Tenant,
                     uid: str,
                     fail_if_not_found: bool = True,
                     fail_if_sealed: bool = False) -> Workitem | None:
        for backlog in self.get_user(data).values():
            if uid in backlog:
                workitem: Workitem = backlog[uid]
                if fail_if_sealed and workitem.is_sealed():
                    raise Exception(f'Workitem "{uid}" is sealed')
                return workitem

        if fail_if_not_found:
            raise Exception(f'Workitem "{uid}" not found')
        else:
            return None

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        timer: TimerData = self.get_user(data).get_timer()
        if timer.is_ticking():
            raise Exception(f'Cannot start timer for workitem {self._workitem_uid}, '
                            f'because it is already running for "{timer.get_running_workitem()}"')

        workitem: Workitem = self.get_workitem(data, self._workitem_uid, True, True)

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

                if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                    pomodoro.update_work_duration(self._work_duration)
                    pomodoro.update_rest_duration(self._rest_duration)

                pomodoro.start_work(self._when)
                pomodoro.item_updated(self._when)

                timer.work(pomodoro, pomodoro.get_work_duration(), self._when)
                emit(events.TimerWorkStart, {
                    'timer': timer,
                }, self._carry)

                emit(events.AfterPomodoroWorkStart, params, self._carry)
                return

        raise Exception(f'No startable pomodoro in "{self._workitem_uid}"')


# StopTimer("")
# This strategy assumes an explicit stop by the end user. Timer rings do not produce this strategy.
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

    def requires_sealing(self) -> bool:
        return True

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        timer: TimerData = self.get_user(data).get_timer()
        if timer.is_idling():
            raise Exception('Cannot stop the timer, because it is not running')

        pomodoro = timer.get_running_pomodoro()

        if pomodoro.get_type() not in [POMODORO_TYPE_TRACKER, POMODORO_TYPE_NORMAL]:
            raise Exception(f'Cannot stop the timer for a running pomodoro of type {pomodoro.get_type()}')

        if pomodoro.get_type() == POMODORO_TYPE_NORMAL and (pomodoro.get_rest_duration() > 0 or pomodoro.is_working()):
            # Stopping a normal running pomodoro with predefined rest duration means voiding it
            params = {
                'pomodoro': pomodoro,
                'reason': 'Voided automatically because you completed the workitem while the timer was running.',
            }
            emit(events.BeforePomodoroVoided, params, self._carry)
            pomodoro.void(self._when)
            pomodoro.item_updated(self._when)

            timer.idle(self._when)
            timer.item_updated(self._when)
            emit(events.TimerRestComplete, {
                'timer': timer,
                'pomodoro': pomodoro,
            }, self._carry)

            emit(events.AfterPomodoroVoided, params, self._carry)
        else:
            # We either stop a pomodoro with unlimited rest period, during rest; or a tracker -- it's a
            # normal completion then
            params = {
                'pomodoro': pomodoro,
            }
            emit(events.BeforePomodoroComplete, params, self._carry)
            pomodoro.seal(self._when)
            pomodoro.item_updated(self._when)

            timer.idle(self._when)
            timer.item_updated(self._when)
            emit(events.TimerRestComplete, {
                'timer': timer,
                'pomodoro': pomodoro,
            }, self._carry)

            emit(events.AfterPomodoroComplete, params, self._carry)


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
                data: Tenant) -> None:
        timer: TimerData = self.get_user(data).get_timer()
        if timer.is_idling():
            raise Exception('The timer rings, but it was not running')

        pomodoro: Pomodoro = timer.get_running_pomodoro()
        if timer.is_working():
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                params = {
                    'pomodoro': pomodoro,
                    'rest_duration': pomodoro.get_rest_duration(),
                }
                emit(events.BeforePomodoroRestStart, params, self._carry)
                pomodoro.start_rest(self._when)
                pomodoro.item_updated(self._when)
                timer.rest(pomodoro.get_rest_duration(), self._when)
                timer.item_updated(self._when)
            else:
                raise Exception('The timer should not ring for a tracker pomodoro')

            emit(events.TimerWorkComplete, {
                'timer': timer,
                'pomodoro': pomodoro,
            }, self._carry)

            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                emit(events.AfterPomodoroRestStart, params, self._carry)
            else:
                emit(events.AfterPomodoroComplete, params, self._carry)

        elif timer.is_resting():
            params = {
                'timer': timer,
                'pomodoro': pomodoro,
            }
            emit(events.BeforePomodoroComplete, params, self._carry)

            pomodoro.seal(self._when)
            pomodoro.item_updated(self._when)

            timer.idle(self._when)
            timer.item_updated(self._when)
            emit(events.TimerRestComplete, {
                'timer': timer,
                'pomodoro': pomodoro,
            }, self._carry)

            emit(events.AfterPomodoroComplete, params, self._carry)


######################################################
################## DEPRECATED STUFF ##################
######################################################

# StartWork("123-456-789", "1500", ["300"])
# DEPRECATED, use StartTimerStrategy instead
@strategy
class StartWorkStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _work_duration: float
    _rest_duration: float

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
        self._work_duration = float(params[1])
        if len(params) == 3:
            self._rest_duration = float(params[2])
        else:
            self._rest_duration = settings.get_rest_duration()

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        self.execute_another(emit,
                             data,
                             StartTimerStrategy,
                             [self._workitem_uid, self._work_duration, self._rest_duration])


# VoidPomodoro("123-456-789")
# DEPRECATED, use StopTimerStrategy instead
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

    def requires_sealing(self) -> bool:
        return True

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        self.execute_another(emit,
                             data,
                             StopTimerStrategy,
                             [])


# FinishTracking("123-456-789")
# DEPRECATED, use StopTimerStrategy instead
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

    def requires_sealing(self) -> bool:
        return True

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        self.execute_another(emit,
                             data,
                             StopTimerStrategy,
                             [])

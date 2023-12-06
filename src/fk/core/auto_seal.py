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

from typing import Iterable, Callable, Type

from fk.core.abstract_strategy import AbstractStrategy
from fk.core.pomodoro_strategies import CompletePomodoroStrategy, StartRestStrategy
from fk.core.workitem import Workitem


def auto_seal(workitems: Iterable[Workitem],
              delta: int,
              executor: Callable[[Type[AbstractStrategy], list[str]], None]) -> None:
    # If there are pomodoros which should have been completed X seconds ago, but are not,
    # then void them automatically.
    for workitem in workitems:
        for pomodoro in workitem.values():
            if pomodoro.is_running():
                remaining_time = pomodoro.total_remaining_time()
                if remaining_time + delta < 0:
                    # This pomodoro has completely expired, i.e. work + rest happened in the past
                    executor(CompletePomodoroStrategy, [workitem.get_uid(), 'canceled'], False)
                    print(f'Warning - automatically voided a pomodoro on '
                          f'{workitem.get_name()} '
                          f'(transition happened when the client was offline)')
                elif pomodoro.is_working():
                    remaining_time = pomodoro.remaining_time_in_current_state()
                    if remaining_time + delta < 0:
                        # This pomodoro should've transitioned to "rest" in the past, but it hasn't
                        # quite expired yet
                        executor(StartRestStrategy, [workitem.get_uid(), str(pomodoro.get_rest_duration())], False)
                        # TODO: This leaves the timer in "Rest: 00:00" state and nothing gets scheduled
                        print(f'Warning - automatically started rest on '
                              f'{workitem.get_name()} '
                              f'(transition happened when the client was offline)')

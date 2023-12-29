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

from typing import TypeVar, Self, Callable, Iterable

from PySide6.QtCore import QThreadPool, Slot

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem

TRoot = TypeVar('TRoot')


class ThreadedEventSource(AbstractEventSource[TRoot]):
    _thread_pool: QThreadPool
    _wrapped: AbstractEventSource[TRoot]

    def __init__(self, wrapped: AbstractEventSource[TRoot]):
        super().__init__(wrapped._settings)
        self._thread_pool = QThreadPool()
        self._wrapped = wrapped

    def start(self, mute_events=True) -> None:
        @Slot()
        def job():
            self._wrapped.start(mute_events)
        self._thread_pool.start(job)

    def get_data(self) -> TRoot:
        return self._wrapped.get_data()

    def get_name(self) -> str:
        return self._wrapped.get_name()

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        return self._wrapped._append(strategies)

    def clone(self, new_root: TRoot) -> Self:
        return self._wrapped.clone(new_root)

    def on(self, event_pattern: str, callback: Callable) -> None:
        self._wrapped.on(event_pattern, callback)

    def cancel(self, event_pattern: str) -> None:
        self._wrapped(event_pattern)

    def unmute(self) -> None:
        self._wrapped.unmute()

    def mute(self) -> None:
        self._wrapped.mute()

    def get_config_parameter(self, name: str) -> str:
        return self._wrapped.get_config_parameter(name)

    def set_config_parameter(self, name: str, value: str) -> str:
        return self._wrapped.set_config_parameter(name, value)

    def execute(self,
                strategy_class:
                type[AbstractStrategy],
                params: list[str],
                persist: bool = True,
                auto: bool = False,
                carry: any = None) -> None:
        self._wrapped.execute(strategy_class, params, persist, auto, carry)

    def auto_seal(self) -> None:
        self._wrapped.auto_seal()

    def backlogs(self) -> Iterable[Backlog]:
        return self._wrapped.backlogs()

    def workitems(self) -> Iterable[Workitem]:
        return self._wrapped.workitems()

    def pomodoros(self) -> Iterable[Pomodoro]:
        return self._wrapped.pomodoros()

    def export(self,
               filename: str,
               new_root: Self,
               start_callback: Callable[[int], None],
               progress_callback: Callable[[int, int], None],
               completion_callback: Callable[[int], None]) -> None:
        self._wrapped.export(filename, new_root, start_callback, progress_callback, completion_callback)

    def import_(self,
                filename: str,
                start_callback: Callable[[int], None],
                progress_callback: Callable[[int, int], None],
                completion_callback: Callable[[int], None]) -> None:
        self._wrapped.import_(filename, start_callback, progress_callback, completion_callback)

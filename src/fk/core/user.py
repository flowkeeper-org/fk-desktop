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
from __future__ import annotations

import datetime

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.backlog import Backlog
from fk.core.category import Category
from fk.core.pomodoro import POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER
from fk.core.tags import Tags
from fk.core.timer_data import TimerData


class User(AbstractDataContainer[Backlog, 'Tenant']):
    _is_system_user: bool
    _tags: Tags
    _root_category: Category
    _timer: TimerData

    def __init__(self,
                 data: 'Tenant',
                 identity: str,
                 name: str,
                 create_date: datetime.datetime,
                 is_system_user: bool):
        super().__init__(name, data, identity, create_date)
        self._is_system_user = is_system_user
        self._tags = Tags(self)
        self._root_category = Category('Root category', 'root', self, create_date)
        self._timer = TimerData(self, create_date)

    def __str__(self):
        return f'User "{self.get_name()} <{self.get_uid()}>"'

    def get_identity(self) -> str:
        return self.get_uid()

    def is_system_user(self) -> bool:
        return self._is_system_user

    # Returns (state, total remaining). State can be Focus, Rest and Idle
    def get_state(self, when: datetime.datetime) -> (str, int):
        p = self._timer.get_running_pomodoro()
        if p is not None and p.get_type() == POMODORO_TYPE_NORMAL and p.is_working():
            return f"Focus", p.remaining_minutes_in_current_state_str(when)
        elif p is not None and p.get_type() == POMODORO_TYPE_NORMAL and p.is_resting():
            return "Rest", p.remaining_minutes_in_current_state_str(when)
        elif p is not None and p.get_type() == POMODORO_TYPE_TRACKER:
            return "Tracking", 0
        else:
            return "Idle", 0

    def get_tags(self) -> Tags:
        return self._tags

    def get_categories(self) -> Category:
        return self._root_category

    def get_timer(self) -> TimerData:
        return self._timer

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        return f'{super().dump(indent, mask_uid, mask_last_modified)}\n' \
               f'{indent}  System user: {self._is_system_user}'
        # TODO: Dump tags, timer and categories

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['is_system_user'] = self._is_system_user
        return d

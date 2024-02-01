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

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.backlog import Backlog
from fk.core.pomodoro import Pomodoro


class User(AbstractDataContainer[Backlog, 'Tenant']):
    _is_system_user: bool
    _last_pomodoro: Pomodoro

    def __init__(self,
                 data: 'Tenant',
                 identity: str,
                 name: str,
                 create_date: datetime.datetime,
                 is_system_user: bool):
        super().__init__(name, data, identity, create_date)
        self._last_pomodoro = None
        self._is_system_user = is_system_user

    def __str__(self):
        return f'User "{self.get_name()} <{self.get_uid()}>"'

    def get_identity(self) -> str:
        return self.get_uid()

    def is_system_user(self) -> bool:
        return self._is_system_user

    # Returns (state, total remaining). State can be Unknown, Focus, Rest and Idle
    def get_state(self) -> (str, int):
        if self._last_pomodoro is None:
            return "Unknown", 0
        remaining = self._last_pomodoro.remaining_time_in_current_state()
        if self._last_pomodoro.is_running():
            return "Focus", remaining
        elif remaining > 0:
            return "Rest", remaining
        else:
            return "Idle", 0

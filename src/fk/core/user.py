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

    def __init__(self,
                 data: 'Tenant',
                 identity: str,
                 name: str,
                 create_date: datetime.datetime,
                 is_system_user: bool):
        super().__init__(name, data, identity, create_date)
        self._is_system_user = is_system_user

    def __str__(self):
        return f'User "{self.get_name()} <{self.get_uid()}>"'

    def get_identity(self) -> str:
        return self.get_uid()

    def is_system_user(self) -> bool:
        return self._is_system_user

    def get_running_pomodoro(self) -> Pomodoro | None:
        for b in self.values():
            for w in b.values():
                if w.is_running():
                    for p in w.values():
                        if p.is_running():
                            return p

    # Returns (state, total remaining). State can be Focus, Rest and Idle
    def get_state(self) -> (str, int):
        p = self.get_running_pomodoro()
        if p is not None and p.is_working():
            return f"Focus", p.remaining_minutes_in_current_state()
        elif p is not None and p.is_resting():
            return "Rest", p.remaining_minutes_in_current_state()
        else:
            return "Idle", 0

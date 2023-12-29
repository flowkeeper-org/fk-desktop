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
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem


class Backlog(AbstractDataContainer[Workitem, 'User']):
    """Backlog is a named list of workitems, belonging to a User."""

    def __init__(self,
                 name: str,
                 user: 'User',
                 uid: str,
                 create_date: datetime.datetime):
        super().__init__(name=name, parent=user, uid=uid, create_date=create_date)

    def __str__(self):
        return f'Backlog "{self._name}"'

    def get_running_workitem(self) -> (Workitem, Pomodoro):
        for workitem in self._children.values():
            for pomodoro in workitem:
                if pomodoro.is_running():
                    return workitem, pomodoro
        return None, None

    def is_today(self) -> bool:
        # "Today" = Created within the last 12 hours
        return (datetime.datetime.now(tz=datetime.timezone.utc) - self.get_create_date()).total_seconds() < 3600 * 12

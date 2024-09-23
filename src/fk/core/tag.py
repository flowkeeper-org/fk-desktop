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
import logging
from typing import Set

from fk.core.abstract_data_item import AbstractDataItem
from fk.core.workitem import Workitem

logger = logging.getLogger(__name__)


class Tag(AbstractDataItem['Tags']):
    _workitems: Set[Workitem]

    def __init__(self,
                 name: str,
                 user: 'User',
                 create_date: datetime.datetime):
        super().__init__(uid=name,
                         parent=user.get_tags(),
                         create_date=create_date)
        self._workitems = set[Workitem]()

    def __str__(self):
        return f'#{self.get_uid()}'

    def get_workitems(self) -> Set[Workitem]:
        return self._workitems

    def add_workitem(self, workitem: Workitem) -> None:
        self._workitems.add(workitem)

    def remove_workitem(self, workitem: Workitem) -> None:
        self._workitems.remove(workitem)

    def dump(self, indent: str = '') -> str:
        return f'{super().dump(indent)}\n' \
               f'{indent} - Name: {self.get_uid()}'

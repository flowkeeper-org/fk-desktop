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

from fk.core.abstract_data_container import AbstractDataContainer

logger = logging.getLogger(__name__)


class Category(AbstractDataContainer['Category', 'Category|User']):
    def __init__(self,
                 name: str,
                 uid: str,
                 parent: 'Category|User',
                 create_date: datetime.datetime):
        super().__init__(name=name,
                         uid=uid,
                         parent=parent,
                         create_date=create_date)

    def __str__(self):
        return f'Category {self.get_uid()} - {self._name}'

    def is_root(self) -> bool:
        return self.get_uid() == 'root'

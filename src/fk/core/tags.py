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

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.tag import Tag


class Tags(AbstractDataContainer[Tag, 'User']):
    def __init__(self, user: 'User'):
        super().__init__(f'Tags',
                         user,
                         f'tags-{user.get_identity()}',
                         user.get_create_date())

    def __str__(self):
        return f'Tags {self.get_name()}'

    def dump(self, indent: str = '', mask_uid: bool = False) -> str:
        return f'{super().dump(indent, mask_uid)}\n' \
               f'{indent} - Tags'

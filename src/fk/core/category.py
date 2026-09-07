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
import textwrap

from fk.core.abstract_data_container import AbstractDataContainer

logger = logging.getLogger(__name__)


def h2(text: str) -> str:
    return f'### <h2 style="font-family: Noto Sans, Sans-serif;">{text.upper()}</h2>'


# TODO: Do not allow delimiters in category names
class Category(AbstractDataContainer['Category', 'Category|User']):
    _is_system: bool
    _info: str
    _uses: set['AbstractCategorizedDataContainer']

    def __init__(self,
                 name: str,
                 uid: str,
                 is_system: bool,
                 info: str,
                 parent: 'Category|User',
                 create_date: datetime.datetime):
        super().__init__(name=name,
                         uid=uid,
                         parent=parent,
                         create_date=create_date)
        self._is_system = is_system
        self._info = info
        self._uses = set()

    def __str__(self):
        return f'Category {self.get_uid()} - {self._name}{" (system)" if self._is_system else ""}, {len(self._uses)} uses'

    def is_root(self) -> bool:
        return self.get_uid() == '#root'

    def is_system(self) -> bool:
        return self._is_system

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        info = ("<" + str(len(self._info)) + "> characters\n") if self._info is not None else "None\n"
        return f'{super().dump(indent, mask_uid, mask_last_modified)}\n' \
               f'{indent}  System: {self._is_system}\n' \
               f'{indent}  Info: {info}' \
               f'{indent}  Uses: <{len(self._uses)}>'

    def get_info(self):
        if self._info is not None and self._info != '':
            return f'''
{h2(self.get_short_name())}

{self._info}
'''
        else:
            return f'''{h2(self.get_short_name())}

*No description*
'''

    def get_short_name(self) -> str:
        name = self.get_name()
        if '(' in name:
            return name[:name.index('(')].strip()
        else:
            return name

    def get_plaintext_info(self):
        txt = self._info if self._info else self._name
        paragraphs = filter(
            lambda p: not p.startswith('Details:'),
            txt.strip().replace('**', '').split('\n\n')
        )
        return "\n\n".join([textwrap.fill(s, 80) for s in paragraphs])

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['is_system'] = self._is_system
        return d

    def add_usage(self, usage: 'AbstractCategorizedDataContainer'):
        self._uses.add(usage)

    def remove_usage(self, usage: 'AbstractCategorizedDataContainer'):
        self._uses.remove(usage)

    def get_uses(self):
        return self._uses

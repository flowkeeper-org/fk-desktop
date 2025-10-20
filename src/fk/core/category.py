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


def create_system_categories(root: Category, now: datetime.datetime) -> None:
    root['#none'] = Category('Uncategorized', '#none', True, root, now)

    wg = root['#workitem_groups'] = Category('Workitem Groups', '#workitem_groups', True, root, now)

    gr = wg['#workitem_group_importance'] = Category('Importance', '#workitem_group_importance', True, wg, now)
    gr['#workitem_group_importance_critical'] = Category('Critical', '#workitem_group_importance_critical', True, gr, now)
    gr['#workitem_group_importance_important'] = Category('Important', '#workitem_group_importance_important', True, gr, now)
    gr['#workitem_group_importance_unimportant'] = Category('Unimportant', '#workitem_group_importance_unimportant', True, gr, now)

    gr = wg['#workitem_group_feasibility'] = Category('Feasibility', '#workitem_group_feasibility', True, wg, now)

    root['#workitem_shares'] = Category('Workitem Shares', '#workitem_shares', True, root, now)
    root['#workitem_integrations'] = Category('Workitem Integrations', '#workitem_integrations', True, root, now)
    root['#workitem_tags'] = Category('Workitem Tags', '#workitem_tags', True, root, now)

    root['#backlog_groups'] = Category('Backlog Groups', '#backlog_groups', True, root, now)
    root['#backlog_shares'] = Category('Backlog Shares', '#backlog_shares', True, root, now)
    root['#backlog_integrations'] = Category('Backlog Integrations', '#backlog_integrations', True, root, now)
    root['#backlog_tags'] = Category('Backlog Tags', '#backlog_tags', True, root, now)


# TODO: Do not allow delimiters in category names
class Category(AbstractDataContainer['Category', 'Category|User']):
    _is_system: bool

    def __init__(self,
                 name: str,
                 uid: str,
                 is_system: bool,
                 parent: 'Category|User',
                 create_date: datetime.datetime):
        super().__init__(name=name,
                         uid=uid,
                         parent=parent,
                         create_date=create_date)
        self._is_system = is_system

    def __str__(self):
        return f'Category {self.get_uid()} - {self._name}{" (system)" if self._is_system else ""}'

    def is_root(self) -> bool:
        return self.get_uid() == '#root'

    def is_system(self) -> bool:
        return self._is_system

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        return f'{super().dump(indent, mask_uid, mask_last_modified)}\n' \
               f'{indent}  System: {self._is_system}'

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['is_system'] = self._is_system
        return d

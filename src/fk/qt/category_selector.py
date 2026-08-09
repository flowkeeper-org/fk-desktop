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

import logging

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QWidget

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings, S
from fk.core.category import Category
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.qt.actions import Actions

logger = logging.getLogger(__name__)


class CategorySelector(QMenu):
    _actions: dict[str, QAction]
    _parent_category: Category

    def __init__(self, parent: QWidget, source_holder: EventSourceHolder) -> None:
        super().__init__(parent)
        self._actions = {}
        self._parent_category = None
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        if source_holder.get_source() is not None:
            self._on_source_changed(None, source_holder.get_source())

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._parent_category = source.find_category('#workitem_groups')
        self._reload_actions(source.get_settings())
        source.on("AfterCategory*", lambda category, **_: self._update_menu_if_needed(category, source.get_settings()))

    def _update_menu_if_needed(self, category: Category, settings: AbstractSettings) -> None:
        if category.get_parent() == self._parent_category:
            self._reload_actions(settings)

    def _on_category_selected(self, selected_uid: str, settings: AbstractSettings):
        for category_uid in self._actions:
            self._actions[category_uid].setChecked(selected_uid == category_uid)
        settings.set({S.APPLICATION_SELECTED_CATEGORY: selected_uid})

    def _on_category_cleared(self, settings: AbstractSettings):
        settings.set({S.APPLICATION_SELECTED_CATEGORY: ''})

    def _create_action(self, cat: Category, selected_category_uid: str, settings: AbstractSettings) -> QAction:
        cat_uid = cat.get_uid()
        action = QAction(cat.get_name(), self)
        action.setCheckable(True)
        action.setObjectName(f'category-selector-{cat_uid}')
        action.setChecked(cat_uid == selected_category_uid)
        action.toggled.connect(lambda checked: self._on_category_selected(cat_uid, settings) if checked else self._on_category_cleared(settings))
        return action

    def _reload_actions(self, settings: AbstractSettings) -> None:
        self.clear()
        self._actions.clear()

        selected_category_uid = settings.get(S.APPLICATION_SELECTED_CATEGORY)
        for sub in self._parent_category.values():
            action = self._create_action(sub, selected_category_uid, settings)
            self._actions[sub.get_uid()] = action
            self.addAction(action)

        self.addSeparator()
        self.addAction(Actions.ALL['application.manageCategories'])

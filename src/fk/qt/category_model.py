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

from PySide6 import QtGui, QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.category import Category
from fk.core.category_strategies import RenameCategoryStrategy, ReorderCategoryStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.qt.abstract_drop_model import AbstractDropModel

logger = logging.getLogger(__name__)
font_user = QtGui.QFont()
font_back = QtGui.QFont()
font_back.setBold(True)
font_system = QtGui.QFont()
font_system.setItalic(True)


class CategoryItem(QStandardItem):
    _category: Category
    _is_back: bool

    def __init__(self, category: Category, is_back: bool = False):
        super().__init__()
        self._category = category
        self._is_back = is_back
        self.setData(category, 500)
        self.setData('title', 501)
        self.setData(is_back, 502)
        default_flags = (Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsDragEnabled |
                         Qt.ItemFlag.ItemIsEditable)
        self.setFlags(default_flags)
        self.update_display()
        self.update_font()

    def update_display(self):
        if self._is_back:
            self.setData('Go back', Qt.ItemDataRole.ToolTipRole)
            self.setData('[..]', Qt.ItemDataRole.DisplayRole)
        else:
            self.setData(self._category.get_name(), Qt.ItemDataRole.ToolTipRole)
            self.setData(self._category.get_name(), Qt.ItemDataRole.DisplayRole)

    def update_font(self):
        if self._is_back:
            font = font_back
        elif self._category.is_system():
            font = font_system
        else:
            font = font_user
        self.setData(font, Qt.ItemDataRole.FontRole)


class CategoryModel(AbstractDropModel):
    _parent_category: Category

    def __init__(self,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(1, parent, source_holder)
        self._parent_category = None
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.itemChanged.connect(lambda item: self.handle_rename(item, RenameCategoryStrategy))
        if source_holder.get_source() is not None:
            self._on_source_changed(None, source_holder.get_source())

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.load(None)
        source.on(events.AfterCategoryCreate, self._category_added)
        source.on(events.AfterCategoryDelete, self._category_removed)
        source.on(events.AfterCategoryRename, self._category_renamed)
        source.on(events.AfterCategoryReorder, self._category_reordered)

    def _category_added(self, category: Category, **kwargs) -> None:
        self.insertRow(0, CategoryItem(category))

    def _category_removed(self, category: Category, **kwargs) -> None:
        for i in range(self.rowCount()):
            cat = self.item(i).data(500)
            if cat == category:
                self.removeRow(i)
                return

    def _category_renamed(self, category: Category, **kwargs) -> None:
        for i in range(self.rowCount()):
            cat = self.item(i).data(500)
            if cat == category:
                self.item(i).update_display()
                return

    def _category_reordered(self, category: Category, new_index: int, carry: str, **kwargs) -> None:
        if carry != 'ui':
            for old_index in range(self.rowCount()):
                cat = self.item(old_index).data(500)
                if cat == category:
                    new_index = self.rowCount() - new_index
                    if new_index > old_index:
                        new_index -= 1
                    row = self.takeRow(old_index)
                    self.insertRow(new_index, row)
                    return

    def load(self, parent_category: Category | None) -> None:
        self._parent_category = parent_category
        self.clear()
        if parent_category is not None:
            # This is a commander-like way to navigate through the categories
            # if not parent_category.is_root():
            #     self.appendRow(CategoryItem(None, True))
            for category in reversed(parent_category.values()):
                self.appendRow(CategoryItem(category))
        self.setHorizontalHeaderItem(0, QStandardItem(''))

    def get_primary_type(self) -> str:
        return 'application/flowkeeper.category.id'

    def item_for_object(self, category: Category) -> list[QStandardItem]:
        return [CategoryItem(category)]
    
    def reorder(self, to_index: int, uid: str):
        self._source_holder.get_source().execute(ReorderCategoryStrategy,
                                                 # We display categories in reverse order, so need to subtract here
                                                 [uid, str(self.rowCount() - to_index)],
                                                 carry='ui')

    def get_parent_category(self):
        return self._parent_category

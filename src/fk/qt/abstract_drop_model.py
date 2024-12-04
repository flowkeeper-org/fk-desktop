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

from abc import ABC, abstractmethod

from PySide6 import QtCore
from PySide6.QtCore import Qt, QMimeData, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel

from fk.core.abstract_data_item import AbstractDataItem
from fk.core.event_source_holder import EventSourceHolder


class DropPlaceholderItem(QStandardItem):
    def __init__(self):
        super().__init__()
        self.setData(None, 500)
        self.setData('drop', 501)
        default_flags = (Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsDropEnabled)
        self.setFlags(default_flags)
        self.setData('', Qt.ItemDataRole.DisplayRole)


class AbstractDropModel(QStandardItemModel):
    _source_holder: EventSourceHolder

    def __init__(self,
                 columns: int,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(0, columns, parent)
        self._source_holder = source_holder

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        if where.data(501) == 'drop':
            item_id = data.data(self.get_type()).toStdString()
            self.reorder(where.row(), item_id)
            self._remove_drop_placeholder()
            self.insertRow(where.row(), self.item_by_id(item_id))
        return True

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def item_by_id(self, uid: str):
        pass

    @abstractmethod
    def reorder(self, to_index: int, uid: str):
        pass

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        return data.data(self.get_type()) is not None

    def mimeTypes(self):
        return [self.get_type()]

    def mimeData(self, indexes):
        if len(indexes) != 1:
            raise Exception(f'Unexpected number of rows to move: {len(indexes)}')
        data = QMimeData()
        item: AbstractDataItem = indexes[0].data(500)
        data.setData(self.get_type(), bytes(item.get_uid(), 'iso8859-1'))
        return data

    def _remove_drop_placeholder(self):
        # We can only have one placeholder
        for i in range(self.rowCount()):
            if self.index(i, 0).data(501) == 'drop':
                self.removeRow(i)
                return  # We won't have more than one

    def create_drop_placeholder(self, index: QModelIndex):
        self._remove_drop_placeholder()
        item = DropPlaceholderItem()
        self.insertRow(index.row(), item)

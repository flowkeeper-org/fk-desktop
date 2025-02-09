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

from abc import abstractmethod

from PySide6 import QtCore
from PySide6.QtCore import Qt, QMimeData, QModelIndex, QSize
from PySide6.QtGui import QStandardItem, QStandardItemModel

from fk.core.abstract_data_item import AbstractDataItem
from fk.core.event_source_holder import EventSourceHolder


class DropPlaceholderItem(QStandardItem):
    def __init__(self, height: int):
        super().__init__()
        self.setData(None, 500)
        if height > 0:
            self.setData(QSize(1, height), Qt.ItemDataRole.SizeHintRole)
        self.setData('drop', 501)
        flags = (Qt.ItemFlag.ItemIsSelectable |
                 Qt.ItemFlag.ItemIsEnabled |
                 Qt.ItemFlag.ItemIsDropEnabled)
        self.setFlags(flags)


class AbstractDropModel(QStandardItemModel):
    _source_holder: EventSourceHolder
    _dragging_row: int | None
    _dragging_uid: str | None

    def __init__(self,
                 columns: int,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(0, columns, parent)
        self._source_holder = source_holder
        self._dragging_row = None
        self._dragging_uid = None

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        print('AbstractDropModel - dropMimeData', data, action, row, column, where.data(501), where.isValid())
        if where.data(501) == 'drop' and data.hasFormat(self.get_type()):
            item_id = data.data(self.get_type()).toStdString()
            self.reorder(where.row(), item_id)
            self.remove_drop_placeholder()
            self.insertRow(where.row(), self.item_by_id(item_id))
            print('Reordered')
            return False
        else:
            print('Dropped somewhere else')
            self.remove_drop_placeholder()
            return False

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
        print('AbstractDropModel - canDropMimeData', where.isValid())
        value = data.data(self.get_type())
        return value is not None and value != b'' and where.isValid()

    def mimeTypes(self):
        return [self.get_type()]

    def mimeData(self, indexes):
        if len(indexes) != 1:
            raise Exception(f'Unexpected number of rows to move: {len(indexes)}')
        data = QMimeData()
        item: AbstractDataItem = indexes[0].data(500)
        data.setData(self.get_type(), bytes(item.get_uid(), 'iso8859-1'))
        return data

    def _find_drop_placeholder(self) -> int | None:
        for i in range(self.rowCount()):
            if self.index(i, 0).data(501) == 'drop':
                return i    # We won't have more than one placeholder
        return None

    def remove_drop_placeholder(self) -> int:
        i = self._find_drop_placeholder()
        if i is not None:
            self.removeRow(i)
            # Restore the original row we removed when we started dragging
            print('Restoring', self._dragging_row, i)
            self.insertRow(self._dragging_row,
                           self.item_by_id(self._dragging_uid))
            print(f'Restored original {self._dragging_uid}')
            inserted = self._dragging_row
            self._dragging_row = None
            self._dragging_uid = None
            return inserted

    def _insert_placeholder(self, row: int, height: int):
        items = [DropPlaceholderItem(height) for _ in range(0, self.columnCount())]
        self.insertRow(row, items)

    def create_drop_placeholder(self, index: QModelIndex, height: int):
        print(f'Original height: {height}')
        self._dragging_row = index.row()
        self._dragging_uid = index.data(500).get_uid()
        print(f'Saved original {self._dragging_uid} at {self._dragging_row}')
        self.removeRow(index.row())
        self._insert_placeholder(index.row(), height)
        print(f'Created drop placeholder at {index}')

    def move_drop_placeholder(self, index: QModelIndex):
        i = self._find_drop_placeholder()
        if i is not None and i != index.row():
            size: QSize = self.index(i, 0).data(Qt.ItemDataRole.SizeHintRole)
            if size is not None:
                height = size.height()
            else:
                height = 0

            self.removeRow(i)
            self._insert_placeholder(index.row(), height)
            print(f'Moved drop placeholder to {index}')

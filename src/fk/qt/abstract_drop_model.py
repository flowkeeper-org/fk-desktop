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
from abc import abstractmethod

from PySide6 import QtCore
from PySide6.QtCore import Qt, QMimeData, QModelIndex, QSize
from PySide6.QtGui import QStandardItem, QStandardItemModel, QColor
from PySide6.QtWidgets import QMessageBox

from fk.core.abstract_data_container import AbstractDataContainer
from fk.core.abstract_data_item import AbstractDataItem
from fk.core.abstract_serializer import sanitize_user_input
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.event_source_holder import EventSourceHolder

logger = logging.getLogger(__name__)


class DropPlaceholderItem(QStandardItem):
    def __init__(self, original: AbstractDataItem, original_display: str, original_index: int):
        super().__init__()
        self.setData(original, 500)
        self.setData('drop', 501)
        self.setData(original_index, 502)
        self.setData(original_display, Qt.ItemDataRole.DisplayRole)
        self.setData(QColor('gray'), Qt.ItemDataRole.ForegroundRole)
        self.setFlags(Qt.ItemFlag.ItemIsSelectable |
                      Qt.ItemFlag.ItemIsEnabled |
                      Qt.ItemFlag.ItemIsDropEnabled)


class AbstractDropModel(QStandardItemModel):
    _source_holder: EventSourceHolder
    dragging: QModelIndex | None

    def __init__(self,
                 columns: int,
                 parent: QtCore.QObject,
                 source_holder: EventSourceHolder):
        super().__init__(0, columns, parent)
        self._source_holder = source_holder
        self.dragging = None

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.LinkAction

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.LinkAction

    def move_drop_placeholder(self, index: QModelIndex | None):
        if index is None:
            # "Commit"
            for i in range(self.rowCount()):
                if self.item(i).data(501) == 'drop':
                    original_item: AbstractDataItem = self.item(i).data(500)
                    value = self.item_for_object(original_item)
                    for j in range(len(value)):
                        self.setItem(i, j, value[j])
                    break
        elif index.isValid():
            if index.data(501) == 'drop':
                return
            else:
                for i in range(self.rowCount()):
                    if self.item(i).data(501) == 'drop':
                        drop_placeholder_item = self.takeRow(i)
                        self.insertRow(index.row(), drop_placeholder_item)
                        return
                for j in range(self.columnCount()):
                    this = self.index(index.row(), j)
                    self.setItem(index.row(), j, DropPlaceholderItem(this.data(500),
                                                                     this.data(Qt.ItemDataRole.DisplayRole),
                                                                     index.row()))

    def restore_order(self) -> int:
        for i in range(self.rowCount()):
            if self.item(i).data(501) == 'drop':
                original_item: AbstractDataItem = self.item(i).data(500)
                original_index = self.item(i).data(502)
                self.takeRow(i)
                self.insertRow(original_index, self.item_for_object(original_item))
                return original_index

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        if data.hasFormat(self.get_type()) and where.isValid():
            from_index = self.dragging.row()
            to_index = where.row()
            self.move_drop_placeholder(None)
            if from_index == to_index:
                return False
            else:
                self.reorder(to_index if to_index < from_index else to_index + 1,
                             data.data(self.get_type()).toStdString())
                return True
        else:
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

    def handle_rename(self, item: QStandardItem, strategy_class: type[AbstractStrategy]) -> None:
        if item.data(501) == 'title':
            entity: AbstractDataContainer = item.data(500)
            old_name = entity.get_name()
            new_name = sanitize_user_input(item.text())
            if old_name != new_name:
                try:
                    self._source_holder.get_source().execute(strategy_class, [entity.get_uid(), new_name])
                except Exception as e:
                    logger.error(f'Failed to rename {old_name} to {new_name}', exc_info=e)
                    item.setText(old_name)
                    QMessageBox().warning(
                        None,
                        "Cannot rename",
                        str(e),
                        QMessageBox.StandardButton.Ok
                    )

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        print('AbstractDropModel - canDropMimeData', where.isValid())
        return where.isValid() and where.data(501) == 'drop'

    def mimeTypes(self):
        return [self.get_type()]

    def mimeData(self, indexes):
        print('mimeData', indexes)
        if len(indexes) != 1:
            raise Exception(f'Unexpected number of rows to move: {len(indexes)}')
        index = indexes[0]
        self.dragging = index
        data = QMimeData()
        item: AbstractDataItem = index.data(500)
        data.setData(self.get_type(), bytes(item.get_uid(), 'iso8859-1'))
        return data

    @abstractmethod
    def item_for_object(self, obj: AbstractDataItem) -> list[QStandardItem]:
        pass

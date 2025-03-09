import sys

from PySide6.QtCore import Qt, QMimeData, QModelIndex
from PySide6.QtGui import QStandardItem, QStandardItemModel, QDragLeaveEvent, QDragMoveEvent, QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QAbstractItemView
from PySide6.QtWidgets import QTableView
from PySide6.QtWidgets import QWidget


class Item:
    title: str
    def __init__(self, title: str):
        self.title = title


class ItemTitle(QStandardItem):
    _item: Item

    def __init__(self, item: Item):
        super().__init__()
        self._item = item
        self.setData(item, 500)
        self.setData('item', 501)
        self.setData(item.title, Qt.ItemDataRole.DisplayRole)
        self.setFlags(Qt.ItemFlag.ItemIsSelectable |
                      Qt.ItemFlag.ItemIsEnabled |
                      Qt.ItemFlag.ItemIsDragEnabled)


class DropPlaceholder(QStandardItem):
    def __init__(self, original: Item, original_index: int):
        super().__init__()
        self.setData(original, 500)
        self.setData('drop', 501)
        self.setData(original_index, 502)
        self.setData(original.title, Qt.ItemDataRole.DisplayRole)
        self.setData(QColor('gray'), Qt.ItemDataRole.ForegroundRole)
        self.setFlags(Qt.ItemFlag.ItemIsSelectable |
                      Qt.ItemFlag.ItemIsEnabled |
                      Qt.ItemFlag.ItemIsDropEnabled)


class Model(QStandardItemModel):
    dragging: QModelIndex | None

    def __init__(self, parent: QWidget, items: list[Item]):
        super().__init__(0, 1, parent)
        self.dragging = None
        for item in items:
            self.appendRow(ItemTitle(item))

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        return where.isValid() and where.data(501) == 'drop'

    def mimeTypes(self):
        return ['application/item']

    def mimeData(self, indexes):
        print('mimeData')
        if len(indexes) != 1:
            raise Exception(f'Unexpected number of rows to move: {len(indexes)}')
        index = indexes[0]
        # This might look wrong, and typically we'd do this in dragEnterEvent instead,
        # however, in the latter the event coordinates are for the target position,
        # which might be (and often is) in another row. Here we are sure that the
        # index is the dragged item. This will be a take / insert operation. The only
        # issue is that this will substitute the item before it is dragged, which means
        # that we are dragging a placeholder, not an actual item.
        self.dragging = index

        if index.data(501) != 'item':
            raise Exception(f'Trying to drag something unexpected: {index.data(501)}')
        data = QMimeData()
        item: Item = index.data(500)
        data.setData('application/item', bytes(item.title, 'iso8859-1'))

        return data

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.LinkAction

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.LinkAction

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, where: QModelIndex):
        target = data.data(self.mimeTypes()[0]).toStdString()
        print('Dropped', target, where)
        self.move_drop_placeholder(None)
        return True

    def restore_order(self) -> int:
        for i in range(self.rowCount()):
            if self.item(i).data(501) == 'drop':
                original_item: ItemTitle = self.item(i).data(500)
                original_index = self.item(i).data(502)
                self.takeRow(i)
                self.insertRow(original_index, ItemTitle(original_item))
                return original_index

    def move_drop_placeholder(self, index: QModelIndex):
        if index is None:
            # "Commit"
            for i in range(self.rowCount()):
                if self.item(i).data(501) == 'drop':
                    original_item: ItemTitle = self.item(i).data(500)
                    self.setItem(i, ItemTitle(original_item))
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
                self.setItem(index.row(), DropPlaceholder(index.data(500), index.row()))


class TableView(QTableView):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        items = [Item('One'), Item('Two'), Item('Three'), Item('Four'), Item('Five')]
        self.setModel(Model(self, items))
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        print('LEAVE', event)
        model: Model = self.model()
        to_select = model.restore_order()
        if to_select is not None:
            print(f'Selecting {to_select}')
            # self.selectRow(to_select)
        self.clearSelection()
        event.accept()

    def dragEnterEvent(self, event: QDragMoveEvent):
        model: Model = self.model()
        dragging: QModelIndex = model.dragging
        print(f'dragEnterEvent for {dragging}')
        model.move_drop_placeholder(dragging)
        event.accept()

    def dragMoveEvent(self, event: QDragMoveEvent):
        self.clearSelection()
        index: QModelIndex = self.indexAt(event.position().toPoint())
        model: Model = self.model()
        model.move_drop_placeholder(index)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    w = QMainWindow(None)
    w.setCentralWidget(TableView(w))
    w.show()
    sys.exit(app.exec())

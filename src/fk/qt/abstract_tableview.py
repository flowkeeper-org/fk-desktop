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
import logging
from abc import abstractmethod
from typing import TypeVar, Generic

from PySide6.QtCore import Qt, QModelIndex, QItemSelectionModel, QEvent
from PySide6.QtGui import QPainter, QStandardItemModel, QDragMoveEvent, QDragEnterEvent, QDragLeaveEvent
from PySide6.QtWidgets import QTableView, QWidget, QAbstractItemView

from fk.core.abstract_data_item import AbstractDataItem
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder, BeforeSourceChanged
from fk.core.events import SourceMessagesProcessed, AfterSettingsChanged
from fk.qt.actions import Actions

logger = logging.getLogger(__name__)

BeforeSelectionChanged = "BeforeSelectionChanged"
AfterSelectionChanged = "AfterSelectionChanged"

TUpstream = TypeVar('TUpstream', bound=AbstractDataItem)
TDownstream = TypeVar('TDownstream', bound=AbstractDataItem)


class AbstractTableView(QTableView, AbstractEventEmitter, Generic[TUpstream, TDownstream]):
    _source: AbstractEventSource
    _is_data_loaded: bool
    _is_upstream_item_selected: bool
    _actions: Actions
    _placeholder_loading: str
    _placeholder_upstream: str
    _placeholder_empty: str
    _editable_column: int
    _row_height: int

    def __init__(self,
                 parent: QWidget,
                 source_holder: EventSourceHolder,
                 model: QStandardItemModel,
                 name: str,
                 actions: Actions,
                 placeholder_loading: str,
                 placeholder_upstream: str,
                 placeholder_empty: str,
                 editable_column: int):
        super().__init__(parent,
                         allowed_events=[
                             BeforeSelectionChanged,
                             AfterSelectionChanged,
                         ],
                         callback_invoker=source_holder.get_settings().invoke_callback)
        self._source = None
        self._actions = actions
        self._is_data_loaded = False
        self._is_upstream_item_selected = False
        self._placeholder_loading = placeholder_loading
        self._placeholder_upstream = placeholder_upstream
        self._placeholder_empty = placeholder_empty
        self._editable_column = editable_column
        self.setModel(model)

        self.setObjectName(name)
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(10)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDragDropOverwriteMode(False)

        self._update_row_height()

        self.selectionModel().currentRowChanged.connect(self._on_current_changed)

        # This will remove selection, otherwise backlogs would be removed one by one
        source_holder.on(BeforeSourceChanged, lambda event, source: self.reset())
        source_holder.get_settings().on(AfterSettingsChanged, self._on_setting_changed)

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.table_row_height' in new_values:
            self._update_row_height()

    def _update_row_height(self):
        self._row_height = int(self._actions.get_settings().get('Application.table_row_height'))
        self.verticalHeader().setDefaultSectionSize(self._row_height)

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        self._source = source
        self._is_data_loaded = False
        self._is_upstream_item_selected = False
        source.on(SourceMessagesProcessed, self._on_data_loaded)

    def _on_data_loaded(self, event: str, source: AbstractEventSource) -> None:
        logger.debug(f'Data loaded - {self.objectName()}')
        self._is_data_loaded = True
        self.repaint()

    @staticmethod
    def define_actions(actions: Actions):
        pass

    def upstream_selected(self, upstream: TUpstream | None) -> None:
        logger.debug(f'{self.__class__.__name__}.upstream_selected({upstream})')
        if upstream is None:
            self._is_upstream_item_selected = False
        else:
            self._is_upstream_item_selected = True
        self.model().load(upstream)  # Should handle None correctly

    def get_current(self) -> TDownstream | None:
        index = self.currentIndex()
        if index is not None:
            return index.data(500)

    @abstractmethod
    def update_actions(self, selected: TDownstream | None) -> None:
        pass

    def _on_current_changed(self, selected: QModelIndex | None, deselected: QModelIndex | None) -> None:
        after: TDownstream | None = None
        if selected is not None:
            after = selected.data(500)

        before: TDownstream | None = None
        if deselected is not None:
            before = deselected.data(500)

        params = {
            'before': before,
            'after': after,
        }
        self._emit(BeforeSelectionChanged, params)
        self.update_actions(after)
        self._emit(AfterSelectionChanged, params)

    def paintEvent(self, e):
        super().paintEvent(e)

        # We may have four situations:
        # 1. The data source hasn't loaded yet
        # 2. The user hasn't selected an upstream yet
        # 3. There are no items in the upstream
        # 4. There are items to display
        text: str
        if not self._is_data_loaded:
            text = self._placeholder_loading
        elif not self._is_upstream_item_selected:
            text = self._placeholder_upstream
        elif self.model().rowCount() == 0:
            text = self._placeholder_empty
        else:
            return

        painter = QPainter(self.viewport())
        painter.save()
        painter.setPen(self.palette().placeholderText().color())
        painter.drawText(self.viewport().rect(),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         text)
        painter.restore()
        painter.end()

    def select(self, data: TDownstream) -> QModelIndex:
        model = self.model()
        for i in range(model.rowCount()):
            index = model.index(i, self._editable_column)
            if model.data(index, 500) == data:
                self.selectionModel().select(index,
                                             QItemSelectionModel.SelectionFlag.SelectCurrent |
                                             QItemSelectionModel.SelectionFlag.ClearAndSelect |
                                             QItemSelectionModel.SelectionFlag.Rows)
                self.setCurrentIndex(index)
                self.scrollTo(index)
                return index
        raise Exception(f"Trying to select a table item {data}, which does not exist")

    def deselect(self) -> None:
        self.selectionModel().clearSelection()

        # We have to block signals here to avoid triggering AfterSelectionChanged, which would screw up the
        # backlog / tags mutually exclusive selection logic
        self.selectionModel().blockSignals(True)
        self.setCurrentIndex(QModelIndex())
        self.selectionModel().blockSignals(False)

        self.update_actions(None)

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        print('LEAVE')
        super().dragLeaveEvent(event)
        original = self.model().remove_drop_placeholder()
        self.selectRow(original)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # TODO: We don't know if it was an outside enter, or we started dragging
        super().dragEnterEvent(event)
        index: QModelIndex = self.indexAt(event.pos())
        if index.isValid():
            print(f'ENTER: {event}')
            self.deselect()
            self.model().create_drop_placeholder(index, self.rowHeight(index.row()))

    def dragMoveEvent(self, event: QDragMoveEvent):
        index: QModelIndex = self.indexAt(event.pos())
        self.model().move_drop_placeholder(index)
        event.ignore()
        # if index.data(501) == 'title':
        #     # Hovering over a "real" item. Insert a "drop placeholder" here instead.
        #     self.model().move_drop_placeholder(index)
        #     event.ignore()
        # else:
        #     # Hovering over a "drop placeholder" item -- nothing to do
        #     event.acceptProposedAction()
        #     super(QAbstractItemView, self).dragMoveEvent(event)

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

from abc import abstractmethod
from typing import Callable, TypeVar, Generic

from PySide6.QtCore import Qt, QModelIndex, QItemSelectionModel
from PySide6.QtGui import QAction, QPainter, QStandardItemModel, QIcon
from PySide6.QtWidgets import QTableView, QWidget

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import SourceMessagesProcessed

BeforeSelectionChanged = "BeforeSelectionChanged"
AfterSelectionChanged = "AfterSelectionChanged"

TUpstream = TypeVar('TUpstream')
TDownstream = TypeVar('TDownstream')


class AbstractTableView(QTableView, AbstractEventEmitter, Generic[TUpstream, TDownstream]):
    _source: AbstractEventSource
    _is_data_loaded: bool
    _is_upstream_item_selected: bool
    _actions: dict[str, QAction]
    _placeholder_loading: str
    _placeholder_upstream: str
    _placeholder_empty: str
    _editable_column: int
    _row_height: int

    def __init__(self,
                 parent: QWidget,
                 source: AbstractEventSource,
                 model: QStandardItemModel,
                 name: str,
                 actions: dict[str, QAction],
                 placeholder_loading: str,
                 placeholder_upstream: str,
                 placeholder_empty: str,
                 editable_column: int):
        super().__init__(parent,
                         allowed_events=[
                             BeforeSelectionChanged,
                             AfterSelectionChanged,
                         ],
                         callback_invoker=source.get_settings().invoke_callback)
        self._source = None
        self._actions = actions
        self._is_data_loaded = False
        self._is_upstream_item_selected = False
        self._placeholder_loading = placeholder_loading
        self._placeholder_upstream = placeholder_upstream
        self._placeholder_empty = placeholder_empty
        self._editable_column = editable_column
        self.setModel(model)

        self._row_height = int(source.get_config_parameter('Application.table_row_height'))
        self.setObjectName(name)
        self.setTabKeyNavigation(False)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(False)
        self.horizontalHeader().setMinimumSectionSize(10)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(self._row_height)

        my_actions = self.create_actions()
        for a in my_actions:
            actions[a] = my_actions[a]
            parent.addAction(my_actions[a])

        self._on_source_changed("", source)
        self.selectionModel().currentRowChanged.connect(self._on_current_changed)

    def _on_source_changed(self, event, source):
        self._source = source
        self._is_data_loaded = False
        self._is_upstream_item_selected = False
        source.on(SourceMessagesProcessed, self._on_data_loaded)

    def _on_data_loaded(self, event):
        self._is_data_loaded = True
        self.repaint()

    def _create_action(self,
                       text: str,
                       shortcut: str,
                       icon: str | None,
                       member: Callable,
                       is_toggle: bool = False,
                       is_checked: bool = False) -> QAction:
        res: QAction = QAction(text, self)
        res.setShortcut(shortcut)
        if icon is not None:
            res.setIcon(QIcon(icon))
        if is_toggle:
            res.setCheckable(True)
            res.setChecked(is_checked)
            res.toggled.connect(member)
        else:
            res.triggered.connect(member)
        return res

    @abstractmethod
    def create_actions(self) -> dict[str, QAction]:
        pass

    def upstream_selected(self, upstream: TUpstream | None) -> None:
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

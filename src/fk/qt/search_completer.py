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

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import QModelIndex, QItemSelectionModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QTableView

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.workitem import Workitem


class SearchBar(QtWidgets.QLineEdit):
    _source: AbstractEventSource
    _backlogs_table: QTableView
    _workitems_table: QTableView
    _show_completed: bool

    def __init__(self,
                 parent: QtWidgets.QWidget,
                 source: AbstractEventSource,
                 backlogs_table: QTableView,
                 workitems_table: QTableView):
        super().__init__(parent)
        self.setObjectName("search")
        self._source = source
        self._backlogs_table = backlogs_table
        self._workitems_table = workitems_table
        self._show_completed = True
        self.hide()
        self.setPlaceholderText('Search')
        self.installEventFilter(self)

    def _select(self, index: QModelIndex):
        workitem: Workitem = index.data(500)
        backlog: Backlog = workitem.get_parent()

        b_table = self._backlogs_table
        w_table = self._workitems_table
        b_model = b_table.model()
        w_model = w_table.model()
        for i in range(b_model.rowCount()):
            b_index = b_model.index(i, 0)
            if b_model.data(b_index, 500) == backlog:
                b_table.selectionModel().select(b_index,
                                                QItemSelectionModel.SelectionFlag.SelectCurrent |
                                                QItemSelectionModel.SelectionFlag.Rows)
                b_table.scrollTo(b_index)
                # We are lucky -- Qt emits signals synchronously, so we can already select the right workitem
                for j in range(w_model.rowCount()):
                    w_index = w_model.index(j, 1)
                    if w_model.data(w_index, 500) == workitem:
                        w_table.selectionModel().select(w_index,
                                                        QItemSelectionModel.SelectionFlag.SelectCurrent |
                                                        QItemSelectionModel.SelectionFlag.Rows)
                        w_table.scrollTo(w_index)
                        break
                break
        self.hide()

    def show(self) -> None:
        completer = QtWidgets.QCompleter()
        completer.activated[QModelIndex].on(lambda index: self._select(index))
        completer.setFilterMode(QtGui.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtGui.Qt.CaseSensitivity.CaseInsensitive)

        model = QStandardItemModel()
        for wi in self._source.workitems():
            if not self._show_completed and wi.is_sealed():
                continue
            item = QStandardItem()
            item.setText(wi.get_name())
            item.setData(wi, 500)
            model.appendRow(item)
        completer.setModel(model)

        self.setCompleter(completer)
        self.setFocus()
        if not self.isVisible():
            self.setText("")
        super().show()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if widget == self and event.type() == QtCore.QEvent.Type.KeyPress and isinstance(event, QtGui.QKeyEvent):
            if event.matches(QtGui.QKeySequence.StandardKey.Cancel):
                self.hide()
        return False

    def show_completed(self, show: bool) -> None:
        self._show_completed = show

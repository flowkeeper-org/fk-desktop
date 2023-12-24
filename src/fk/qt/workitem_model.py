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

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, QSize

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.events import AfterWorkitemRename, AfterWorkitemComplete, AfterWorkitemStart, AfterWorkitemCreate, \
    AfterWorkitemDelete
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import RenameWorkitemStrategy


class WorkitemModel(QtGui.QStandardItemModel):
    _source: AbstractEventSource
    _font_new: QtGui.QFont
    _font_running: QtGui.QFont
    _font_sealed: QtGui.QFont
    _backlog: Backlog | None
    _row_height: int

    def __init__(self, parent: QtWidgets.QWidget, source: AbstractEventSource):
        super().__init__(0, 3, parent)
        self._source = source
        self._font_new = QtGui.QFont()
        self._font_running = QtGui.QFont()
        self._font_running.setWeight(QtGui.QFont.Weight.Bold)
        self._font_sealed = QtGui.QFont()
        self._font_sealed.setStrikeOut(True)
        self._backlog = None
        source.connect(AfterWorkitemCreate, self._workitem_created)
        source.connect(AfterWorkitemDelete, self._workitem_deleted)
        source.connect(AfterWorkitemRename, self._pomodoro_changed)
        source.connect(AfterWorkitemComplete, self._pomodoro_changed)
        source.connect(AfterWorkitemStart, self._pomodoro_changed)
        source.connect('AfterPomodoro*', self._pomodoro_changed)
        self.itemChanged.connect(lambda item: self._handle_rename(item))
        self._row_height = int(source.get_config_parameter('Application.table_row_height'))

    def _handle_rename(self, item: QtGui.QStandardItem) -> None:
        if item.data(501) == 'title':
            workitem: Workitem = item.data(500)
            old_name = workitem.get_name()
            new_name = item.text()
            if old_name != new_name:
                try:
                    self._source.execute(RenameWorkitemStrategy, [workitem.get_uid(), new_name])
                except Exception as e:
                    item.setText(old_name)
                    QtWidgets.QMessageBox().warning(
                        self.parent(),
                        "Cannot rename",
                        str(e),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

    def _workitem_created(self, event: str, workitem: Workitem) -> None:
        if workitem.get_parent() == self._backlog:
            item = QtGui.QStandardItem('')
            self.appendRow(item)
            self.set_row(self.rowCount() - 1, workitem)

    def _workitem_deleted(self, event: str, workitem: Workitem) -> None:
        if workitem.get_parent() == self._backlog:
            for i in range(self.rowCount()):
                wi = self.item(i).data(500)  # 500 ~ Qt.UserRole + 1
                if wi == workitem:
                    self.removeRow(i)
                    return

    def _pomodoro_changed(self, event: str, workitem: Workitem, **kwargs) -> None:
        for i in range(self.rowCount()):
            wi = self.item(i).data(500)
            if wi == workitem:
                self.set_row(i, wi)
                return

    def set_row(self, i: int, workitem: Workitem) -> None:
        font = self._font_new
        if workitem.is_running():
            font = self._font_running
        elif workitem.is_sealed():
            font = self._font_sealed

        col1 = QtGui.QStandardItem()
        col1.setData('' if workitem.is_planned() else '*', Qt.DisplayRole)
        col1.setData(font, Qt.FontRole)
        col1.setData(workitem, 500)
        col1.setData('planned', 501)
        col1.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.setItem(i, 0, col1)

        col2 = QtGui.QStandardItem()
        col2.setData(workitem.get_name(), Qt.DisplayRole)
        col2.setData(font, Qt.FontRole)
        col2.setData(workitem, 500)
        col2.setData('title', 501)
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if not workitem.is_sealed():
            flags |= Qt.ItemFlag.ItemIsEditable
        col2.setFlags(flags)
        self.setItem(i, 1, col2)

        col3 = QtGui.QStandardItem()
        col3.setData(','.join([str(p) for p in workitem.values()]), Qt.DisplayRole)
        # TODO: Get row height here somehow
        col3.setData(QSize(len(workitem) * self._row_height, self._row_height), Qt.SizeHintRole)
        col3.setData(workitem, 500)
        col3.setData('pomodoro', 501)
        col3.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.setItem(i, 2, col3)

    def load(self, backlog: Backlog) -> None:
        self.clear()
        self._backlog = backlog
        if backlog is not None:
            i = 0
            for workitem in backlog.values():
                item = QtGui.QStandardItem('')
                self.appendRow(item)
                self.set_row(i, workitem)
                i += 1
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))
        self.setHorizontalHeaderItem(1, QtGui.QStandardItem(''))
        self.setHorizontalHeaderItem(2, QtGui.QStandardItem(''))

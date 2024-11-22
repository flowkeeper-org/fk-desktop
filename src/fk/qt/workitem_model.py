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

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, QSize

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemRename, AfterWorkitemComplete, AfterWorkitemStart, AfterWorkitemCreate, \
    AfterWorkitemDelete, AfterSettingsChanged
from fk.core.tag import Tag
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import RenameWorkitemStrategy

logger = logging.getLogger(__name__)


class WorkitemModel(QtGui.QStandardItemModel):
    _source_holder: EventSourceHolder
    _font_new: QtGui.QFont
    _font_running: QtGui.QFont
    _font_sealed: QtGui.QFont
    _backlog_or_tag: Backlog | Tag | None
    _row_height: int
    _show_completed: bool

    def __init__(self, parent: QtWidgets.QWidget, source_holder: EventSourceHolder):
        super().__init__(0, 3, parent)
        self._source_holder = source_holder
        self._font_new = QtGui.QFont()
        self._font_running = QtGui.QFont()
        self._font_running.setWeight(QtGui.QFont.Weight.Bold)
        self._font_sealed = QtGui.QFont()
        self._font_sealed.setStrikeOut(True)
        self._backlog_or_tag = None
        self._show_completed = (source_holder.get_settings().get('Application.show_completed') == 'True')
        self._update_row_height()
        self.itemChanged.connect(lambda item: self._handle_rename(item))
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        source_holder.get_settings().on(AfterSettingsChanged, self._on_setting_changed)

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.table_row_height' in new_values:
            self._update_row_height()

    def _update_row_height(self):
        rh = int(self._source_holder.get_settings().get('Application.table_row_height'))
        self._row_height = rh
        # TODO: Updating existing rows doesn't work.
        #  The right way to do it is by using QStandardItem subclass, like we do for BacklogModel
        # for i in range(self.rowCount()):
        #     item: QStandardItem = self.item(i, 2)
        #     workitem: Workitem = item.data(500)
        #     item.setData(QSize(len(workitem) * rh, rh), Qt.ItemDataRole.SizeHintRole)
        #     self.setItem(i, 2, item)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.load(None)
        source.on(AfterWorkitemCreate, self._workitem_created)
        source.on(AfterWorkitemDelete, self._workitem_deleted)
        source.on(AfterWorkitemRename, self._workitem_renamed)
        source.on(AfterWorkitemComplete, self._pomodoro_changed)
        source.on(AfterWorkitemStart, self._pomodoro_changed)
        source.on('AfterPomodoro*', self._pomodoro_changed)

    def _handle_rename(self, item: QtGui.QStandardItem) -> None:
        if item.data(501) == 'title':
            workitem: Workitem = item.data(500)
            old_name = workitem.get_name()
            new_name = item.text()
            if old_name != new_name:
                try:
                    self._source_holder.get_source().execute(RenameWorkitemStrategy, [workitem.get_uid(), new_name])
                except Exception as e:
                    logger.error(f'Failed to rename {old_name} to {new_name}', exc_info=e)
                    item.setText(old_name)
                    QtWidgets.QMessageBox().warning(
                        self.parent(),
                        "Cannot rename",
                        str(e),
                        QtWidgets.QMessageBox.StandardButton.Ok
                    )

    def _workitem_belongs_here(self, workitem: Workitem) -> bool:
        return (type(self._backlog_or_tag) is Backlog and workitem.get_parent() == self._backlog_or_tag
                or
                type(self._backlog_or_tag) is Tag and self._backlog_or_tag.get_uid() in workitem.get_tags())

    def _add_workitem(self, workitem: Workitem) -> None:
        item = QtGui.QStandardItem('')
        self.appendRow(item)
        self.set_row(self.rowCount() - 1, workitem)

    def _find_workitem(self, workitem: Workitem) -> int:
        for i in range(self.rowCount()):
            wi = self.item(i).data(500)  # 500 ~ Qt.UserRole + 1
            if wi == workitem:
                return i
        return -1

    def _remove_if_found(self, workitem: Workitem) -> None:
        i = self._find_workitem(workitem)
        if i >= 0:
            self.removeRow(i)

    def _workitem_created(self, workitem: Workitem, **kwargs) -> None:
        if self._workitem_belongs_here(workitem):
            self._add_workitem(workitem)

    def _workitem_deleted(self, workitem: Workitem, **kwargs) -> None:
        if self._workitem_belongs_here(workitem):
            self._remove_if_found(workitem)

    def _workitem_renamed(self, workitem: Workitem, old_name: str, new_name: str, **kwargs) -> None:
        if type(self._backlog_or_tag) is Tag:
            if self._backlog_or_tag.get_uid() in workitem.get_tags():
                # This workitem should be in this list
                if self._find_workitem(workitem) < 0:
                    self._add_workitem(workitem)
            else:
                # This workitem should not be in this list
                self._remove_if_found(workitem)
        self._pomodoro_changed(workitem)

    def _pomodoro_changed(self, workitem: Workitem, **kwargs) -> None:
        for i in range(self.rowCount()):
            wi = self.item(i).data(500)
            if wi == workitem:
                if not self._show_completed and workitem.is_sealed():
                    self.removeRow(i)
                else:
                    self.set_row(i, wi)
                return

    def set_row(self, i: int, workitem: Workitem) -> None:
        font = self._font_new
        if workitem.is_running():
            font = self._font_running
        elif workitem.is_sealed():
            font = self._font_sealed

        default_flags = (Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsDragEnabled |
                         Qt.ItemFlag.ItemIsDropEnabled)

        col1 = QtGui.QStandardItem()
        col1.setData('' if workitem.is_planned() else '*', Qt.ItemDataRole.DisplayRole)
        col1.setData(font, Qt.ItemDataRole.FontRole)
        col1.setData(workitem, 500)
        col1.setData('planned', 501)
        col1.setFlags(default_flags)
        self.setItem(i, 0, col1)

        col2 = QtGui.QStandardItem()
        col2.setData(workitem.get_name(), Qt.ItemDataRole.DisplayRole)
        col2.setData(font, Qt.ItemDataRole.FontRole)
        col2.setData(workitem, 500)
        col2.setData('title', 501)
        col2.setData(workitem.get_name(), Qt.ItemDataRole.ToolTipRole)
        flags = default_flags
        if not workitem.is_sealed():
            flags |= Qt.ItemFlag.ItemIsEditable
        col2.setFlags(flags)
        self.setItem(i, 1, col2)

        col3 = QtGui.QStandardItem()
        # Here we rely on the fact that dict.values() stores values in the FIFO order,
        # i.e. acts like a list. I'm not sure if it is guaranteed, but seems to work.
        col3.setData(','.join([str(p) for p in workitem.values()]), Qt.ItemDataRole.DisplayRole)
        col3.setData(QSize(len(workitem) * self._row_height, self._row_height), Qt.ItemDataRole.SizeHintRole)
        col3.setData(workitem, 500)
        col3.setData('pomodoro', 501)
        col3.setFlags(default_flags)
        self.setItem(i, 2, col3)

    def get_row_height(self):
        return self._row_height

    def load(self, backlog_or_tag: Backlog | Tag) -> None:
        logger.debug(f'WorkitemModel.load({backlog_or_tag})')
        self.clear()
        self._backlog_or_tag = backlog_or_tag
        if backlog_or_tag is not None:
            i = 0
            if type(backlog_or_tag) is Backlog:
                workitems = backlog_or_tag.values()
            else:
                workitems = sorted(backlog_or_tag.get_workitems(),
                                   key=lambda a: a.get_last_modified_date())
            for workitem in workitems:
                if not self._show_completed and workitem.is_sealed():
                    continue
                item = QtGui.QStandardItem('')
                self.appendRow(item)
                self.set_row(i, workitem)
                i += 1
        self.setHorizontalHeaderItem(0, QtGui.QStandardItem(''))
        self.setHorizontalHeaderItem(1, QtGui.QStandardItem(''))
        self.setHorizontalHeaderItem(2, QtGui.QStandardItem(''))

    def show_completed(self, show: bool) -> None:
        self._show_completed = show
        self.load(self._backlog_or_tag)

    def get_backlog_or_tag(self) -> Backlog | Tag | None:
        return self._backlog_or_tag

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction

    def insertRows(self, row, count, parent = ...):
        print('insertRows', row, count)
        super().insertRows(row, count, parent)

    def removeRows(self, row, count, parent = ...):
        print('removeRows', row, count)
        super().removeRows(row, count, parent)

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        print('moveRows', sourceRow, count, destinationChild)
        super().moveRows(sourceParent, sourceRow, count, destinationParent, destinationChild)

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
import datetime
import logging

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFontMetrics, QStandardItem
from PySide6.QtWidgets import QApplication

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemRename, AfterWorkitemComplete, AfterWorkitemStart, AfterWorkitemCreate, \
    AfterWorkitemDelete, AfterSettingsChanged, AfterWorkitemReorder
from fk.core.pomodoro import POMODORO_TYPE_TRACKER, Pomodoro
from fk.core.tag import Tag
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import RenameWorkitemStrategy, ReorderWorkitemStrategy
from fk.qt.abstract_drop_model import AbstractDropModel

logger = logging.getLogger(__name__)


class WorkitemPlanned(QStandardItem):
    _workitem: Workitem

    def __init__(self, workitem: Workitem, font: QtGui.QFont):
        super().__init__()
        self._workitem = workitem
        self.setData(workitem, 500)
        self.setData('planned', 501)
        flags = (Qt.ItemFlag.ItemIsSelectable |
                 Qt.ItemFlag.ItemIsEnabled)
        self.setFlags(flags)
        self.update_planned()
        self.update_font(font)

    def update_planned(self):
        self.setData('' if self._workitem.is_planned() else '*', Qt.ItemDataRole.DisplayRole)
        self.setData('Planned work item' if self._workitem.is_planned() else 'Unplanned work item', Qt.ItemDataRole.ToolTipRole)

    def update_font(self, font: QtGui.QFont):
        self.setData(font, Qt.ItemDataRole.FontRole)


class WorkitemTitle(QStandardItem):
    _workitem: Workitem

    def __init__(self, workitem: Workitem, font: QtGui.QFont):
        super().__init__()
        self._workitem = workitem
        self.setData(workitem, 500)
        self.setData('title', 501)
        self.update_display()
        self.update_font(font)
        self.update_flags()

    def update_display(self):
        self.setData(self._workitem.get_name(), Qt.ItemDataRole.DisplayRole)
        self.setData(self._workitem.get_name(), Qt.ItemDataRole.ToolTipRole)

    def update_flags(self):
        flags = (Qt.ItemFlag.ItemIsSelectable |
                 Qt.ItemFlag.ItemIsEnabled |
                 Qt.ItemFlag.ItemIsDragEnabled)
        if not self._workitem.is_sealed():
            flags |= Qt.ItemFlag.ItemIsEditable
        self.setFlags(flags)

    def update_font(self, font: QtGui.QFont):
        self.setData(font, Qt.ItemDataRole.FontRole)


def hhmm(when: datetime.datetime) -> str:
    return when.strftime('%H:%M')


class WorkitemPomodoro(QStandardItem):
    _workitem: Workitem
    _row_height: int

    def __init__(self, workitem: Workitem, row_height: int):
        super().__init__()
        self._workitem = workitem
        self._row_height = row_height
        self.setData(workitem, 500)
        self.setData('pomodoro', 501)
        flags = (Qt.ItemFlag.ItemIsSelectable |
                 Qt.ItemFlag.ItemIsEnabled)
        self.setFlags(flags)
        self.update_display()

    def _list_interruptions(self, pomodoro: Pomodoro, res: list[str]) -> None:
        for i in pomodoro.values():
            reason = f' ({i.get_reason()})' if i.get_reason() else ''
            action = 'Voided' if i.is_void() else 'Interrupted'
            res.append(f' - {action} at {hhmm(i.get_create_date())}{reason}')

    def _format_tooltip(self) -> str:
        res = list()

        for p in self._workitem.values():
            if p.get_type() == POMODORO_TYPE_TRACKER:
                # The fact that we detect it as a tracker means that we started it
                elapsed = round((p.get_last_modified_date() - p.get_work_start_date()).total_seconds())
                res.append(f'Tracked {datetime.timedelta(seconds=elapsed)} '
                           f'from {hhmm(p.get_work_start_date())} to {hhmm(p.get_last_modified_date())}')
                self._list_interruptions(p, res)
            else:
                res.append(f'{p.get_name()} - {"planned" if p.is_planned() else "unplanned"}, {p.get_state()}:')
                res.append(f' - Created at {hhmm(p.get_create_date())}')
                if p.is_working():
                    res.append(f' - Working since {hhmm(p.get_work_start_date())}')
                if p.is_resting() or p.is_finished():
                    res.append(f' - Started work at {hhmm(p.get_work_start_date())}')
                if p.is_resting():
                    res.append(f' - Resting since {hhmm(p.get_rest_start_date())}')
                self._list_interruptions(p, res)
                if p.is_finished():
                    work_duration = round(p.get_elapsed_work_duration())
                    if work_duration > 0:
                        res.append(f' - Worked for {datetime.timedelta(seconds=work_duration)}s')
                    rest_duration = round(p.get_elapsed_rest_duration())
                    if rest_duration > 0:
                        rest_type = ''
                        if p.get_rest_duration() == 0:
                            rest_type = ' (long break)'
                        res.append(f' - Rested for {datetime.timedelta(seconds=rest_duration)}{rest_type}')
                    res.append(f' - Completed at {hhmm(p.get_last_modified_date())}')

        return '\n'.join(res)

    def update_display(self):
        self.setData(','.join([str(p) for p in self._workitem.values()]), Qt.ItemDataRole.DisplayRole)

        if self._workitem.is_tracker():
            elapsed = str(self._workitem.get_total_elapsed_time())
            if self._workitem.has_running_pomodoro():
                elapsed += '+'
            self.setData(elapsed, Qt.ItemDataRole.DisplayRole)
            sz = QFontMetrics(QApplication.font()).horizontalAdvance(elapsed) + 8
        else:
            # Calculate its size, given that voided pomodoros are just narrow ticks
            sz = 0
            for p in self._workitem.values():
                sz += self._row_height
                sz += len(p) * self._row_height / 4     # Voided pomodoro ticks

        self.setData(QSize(sz, self._row_height), Qt.ItemDataRole.SizeHintRole)
        self.setData(self._format_tooltip(), Qt.ItemDataRole.ToolTipRole)


class WorkitemModel(AbstractDropModel):
    _font_new: QtGui.QFont
    _font_running: QtGui.QFont
    _font_sealed: QtGui.QFont
    _backlog_or_tag: Backlog | Tag | None
    _row_height: int
    _hide_completed: bool

    def __init__(self, parent: QtWidgets.QWidget, source_holder: EventSourceHolder):
        super().__init__(1, parent, source_holder)
        self._font_new = QtGui.QFont()
        self._font_running = QtGui.QFont()
        # self._font_running.setWeight(QtGui.QFont.Weight.Bold)
        self._font_sealed = QtGui.QFont()
        self._font_sealed.setStrikeOut(True)
        self._backlog_or_tag = None
        self._hide_completed = (source_holder.get_settings().get('Application.hide_completed') == 'True')
        self._update_row_height()
        self.itemChanged.connect(lambda item: self.handle_rename(item, RenameWorkitemStrategy))
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
        source.on(AfterWorkitemReorder, self._workitem_reordered)
        source.on(AfterWorkitemComplete, self._workitem_changed)
        source.on(AfterWorkitemStart, self._workitem_changed)
        source.on('AfterPomodoro*',
                  lambda **kwargs: self._workitem_changed(
                      kwargs['workitem'] if 'workitem' in kwargs else kwargs['pomodoro'].get_parent()
                  ))

    def _workitem_belongs_here(self, workitem: Workitem) -> bool:
        return (type(self._backlog_or_tag) is Backlog and workitem.get_parent() == self._backlog_or_tag
                or
                type(self._backlog_or_tag) is Tag and self._backlog_or_tag.get_uid() in workitem.get_tags())

    def _add_workitem(self, workitem: Workitem) -> None:
        self.appendRow(self.item_for_object(workitem))

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
        self._workitem_changed(workitem)

    def _workitem_reordered(self, workitem: Workitem, new_index: int, carry: str, **kwargs) -> None:
        if (carry != 'ui' and
                type(self._backlog_or_tag) is Backlog and
                self._workitem_belongs_here(workitem)):
            old_index = self._find_workitem(workitem)
            if old_index >= 0:
                if new_index > old_index:
                    new_index -= 1
                row = self.takeRow(old_index)
                self.insertRow(new_index, row)

    def _workitem_changed(self, workitem: Workitem, **kwargs) -> None:
        for i in range(self.rowCount()):
            item0: WorkitemPlanned = self.item(i, 0)
            wi = item0.data(500)
            if wi == workitem:
                if self._hide_completed and workitem.is_sealed():
                    self.removeRow(i)
                else:
                    font = self._get_font(workitem)
                    item0.update_font(font)
                    item0.update_planned()

                    item1: WorkitemTitle = self.item(i, 1)
                    item1.update_font(font)
                    item1.update_display()
                    item1.update_flags()

                    item2: WorkitemPomodoro = self.item(i, 2)
                    item2.update_display()
                return

    def get_row_height(self):
        return self._row_height

    def load(self, backlog_or_tag: Backlog | Tag) -> None:
        logger.debug(f'WorkitemModel.load({backlog_or_tag})')
        self.clear()
        self._backlog_or_tag = backlog_or_tag
        if backlog_or_tag is not None:
            if type(backlog_or_tag) is Backlog:
                workitems = backlog_or_tag.values()
            else:
                workitems = sorted(backlog_or_tag.get_workitems(),
                                   key=lambda a: a.get_last_modified_date())
            for workitem in workitems:
                if self._hide_completed and workitem.is_sealed():
                    continue
                self.appendRow(self.item_for_object(workitem))
        self.setHorizontalHeaderItem(0, QStandardItem(''))
        self.setHorizontalHeaderItem(1, QStandardItem(''))
        self.setHorizontalHeaderItem(2, QStandardItem(''))

    def hide_completed(self, hide: bool) -> None:
        self._hide_completed = hide
        self.load(self._backlog_or_tag)

    def get_backlog_or_tag(self) -> Backlog | Tag | None:
        return self._backlog_or_tag

    def get_type(self) -> str:
        return 'application/flowkeeper.workitem.id'

    def item_by_id(self, uid: str) -> list[QStandardItem]:
        workitem = self._source_holder.get_source().find_workitem(uid)
        return self.item_for_object(workitem)

    def _get_font(self, workitem: Workitem) -> QtGui.QFont:
        if workitem.is_running():
            return self._font_running
        elif workitem.is_sealed():
            return self._font_sealed
        return self._font_new

    def item_for_object(self, workitem: Workitem) -> list[QStandardItem]:
        font = self._get_font(workitem)
        return [
            WorkitemPlanned(workitem, font),
            WorkitemTitle(workitem, font),
            WorkitemPomodoro(workitem, self._row_height)
        ]

    def reorder(self, to_index: int, uid: str):
        # Convert to_index into the "item index".
        # We are sure it's a Backlog, since reordering is disabled for tags.
        to_add = 0
        visible_index = 0
        if self._hide_completed:
            for item in self._backlog_or_tag.values():
                if item.is_sealed():
                    to_add += 1
                else:
                    visible_index += 1
                    if visible_index >= to_index:
                        break
        logger.debug(f'When reordering {uid} having to add {to_add} items before our target index {to_index}')
        print(f'When reordering {uid} having to add {to_add} items before our target index {to_index}')
        self._source_holder.get_source().execute(ReorderWorkitemStrategy,
                                                 [uid, str(to_index + to_add)],
                                                 carry='ui')

    def repaint_workitem(self, workitem: Workitem):
        for i in range(self.rowCount()):
            wi = self.item(i).data(500)  # 500 ~ Qt.UserRole + 1
            if wi == workitem:
                item: WorkitemPomodoro = self.item(i, 2)
                item.update_display()

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
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFontMetrics, QStandardItem
from PySide6.QtWidgets import QApplication

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import S
from fk.core.backlog import Backlog
from fk.core.category import Category
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemRename, AfterWorkitemComplete, AfterWorkitemStart, AfterWorkitemCreate, \
    AfterWorkitemDelete, AfterSettingsChanged, AfterWorkitemReorder, AfterWorkitemMove, AfterWorkitemRestore, \
    AfterCategoryCreate, AfterCategoryDelete, AfterCategoryRename, AfterCategoryReorder, AfterWorkitemCategoryChange
from fk.core.pomodoro import POMODORO_TYPE_TRACKER, Pomodoro
from fk.core.tag import Tag
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import RenameWorkitemStrategy, ReorderWorkitemStrategy, \
    UpdateWorkitemCategoriesStrategy
from fk.qt.abstract_drop_model import AbstractDropModel, StubItem

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
        # It is important to update display role first, otherwise this might lead to infinite loops
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
    return when.astimezone().strftime('%H:%M')


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
                        res.append(f' - Worked for {datetime.timedelta(seconds=work_duration)}')
                    rest_duration = round(p.get_elapsed_rest_duration())
                    if rest_duration > 0:
                        rest_type = ''
                        if p.get_rest_duration() == 0:
                            rest_type = ' (long break)'
                        res.append(f' - Rested for {datetime.timedelta(seconds=rest_duration)}{rest_type}')
                    res.append(f' - Completed at {hhmm(p.get_last_modified_date())}')

        if self._workitem.is_sealed():
            res.append(f'Marked completed at {hhmm(self._workitem.get_last_modified_date())}')

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


class CategoryItem(QStandardItem):
    _category: Category

    def __init__(self, category: Category, font: QtGui.QFont):
        super().__init__()
        self._category = category
        self.setData('category', 501)
        uid = category.get_uid()
        self.setData(uid, 502)
        self.setFlags(Qt.ItemFlag.NoItemFlags)
        self.update_display()
        self.update_font(font)

    def update_display(self):
        name = self._category.get_name()
        self.setData(name, 503)
        self.setData(name, Qt.ItemDataRole.DisplayRole)
        self.setData(self._category.get_plaintext_info(), Qt.ItemDataRole.ToolTipRole)

    def update_font(self, font: QtGui.QFont):
        self.setData(font, Qt.ItemDataRole.FontRole)

    def get_category(self) -> Category:
        return self._category


class WorkitemModel(AbstractDropModel):
    _font_new: QtGui.QFont
    _font_running: QtGui.QFont
    _font_sealed: QtGui.QFont
    _font_category: QtGui.QFont
    _backlog_or_tag: Backlog | Tag | None
    _row_height: int
    _hide_completed: bool
    _selected_category_uid: str

    data_loaded = Signal(None)

    def __init__(self, parent: QtWidgets.QWidget, source_holder: EventSourceHolder):
        super().__init__(1, parent, source_holder)
        self._font_new = QtGui.QFont()
        self._font_running = QtGui.QFont()
        # self._font_running.setWeight(QtGui.QFont.Weight.Bold)
        self._font_sealed = QtGui.QFont()
        self._font_sealed.setStrikeOut(True)
        self._font_category = QtGui.QFont()
        self._font_category.setBold(True)
        # self._font_category.setUnderline(True)
        self._backlog_or_tag = None
        settings = source_holder.get_settings()
        self._hide_completed = (settings.get(S.APPLICATION_HIDE_COMPLETED) == 'True')
        self._selected_category_uid = settings.get(S.APPLICATION_SELECTED_CATEGORY)
        self._update_row_height(int(settings.get(S.APPLICATION_TABLE_ROW_HEIGHT)))
        self.itemChanged.connect(lambda item: self.handle_rename(item, RenameWorkitemStrategy))
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        settings.on(AfterSettingsChanged, self._on_setting_changed)

        # Pre-create columns, so that we can define their resize policy in the view
        self.setHorizontalHeaderItem(0, QStandardItem(''))
        self.setHorizontalHeaderItem(1, QStandardItem(''))
        self.setHorizontalHeaderItem(2, QStandardItem(''))

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if S.APPLICATION_TABLE_ROW_HEIGHT in new_values:
            self._update_row_height(int(new_values[S.APPLICATION_TABLE_ROW_HEIGHT]))
        if S.APPLICATION_SELECTED_CATEGORY in new_values:
            self._selected_category_uid = new_values[S.APPLICATION_SELECTED_CATEGORY]
            self.load(self._backlog_or_tag)

    def _update_row_height(self, new_height: int):
        self._row_height = new_height
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
        source.on(AfterWorkitemMove, self._workitem_moved)
        source.on(AfterWorkitemCategoryChange, self._workitem_category_changed)
        source.on(AfterWorkitemComplete, self._workitem_changed)
        source.on(AfterWorkitemRestore, self._workitem_changed)
        source.on(AfterWorkitemStart, self._workitem_changed)
        source.on(AfterCategoryCreate, self._category_created)
        source.on(AfterCategoryDelete, self._category_deleted)
        source.on(AfterCategoryRename, self._category_renamed)
        source.on(AfterCategoryReorder, self._category_reordered)
        source.on('AfterPomodoro*',
                  lambda **kwargs: self._workitem_changed(
                      kwargs['workitem'] if 'workitem' in kwargs else kwargs['pomodoro'].get_parent()
                  ))

    def _workitem_belongs_here(self, workitem: Workitem) -> bool:
        return (type(self._backlog_or_tag) is Backlog and workitem.get_parent() == self._backlog_or_tag
                or
                type(self._backlog_or_tag) is Tag and self._backlog_or_tag.get_uid() in workitem.get_tags())

    def _category_belongs_here(self, category: Category) -> bool:
        return (type(self._backlog_or_tag) is Backlog and
                category is not None and
                self._selected_category_uid is not None and
                category.get_parent().get_uid() == self._selected_category_uid)

    def _add_workitem(self, workitem: Workitem) -> None:
        item = self.item_for_object(workitem)
        if self.is_category_selected():
            # Insert at the last uncategorized row
            i = self._get_category_insertion_index(None)
            self.insertRow(i, item)
        else:
            self.appendRow(item)

    def _add_category(self, category: Category) -> None:
        item = self.item_for_category(category)
        self.appendRow(item)
        # Fire dataChanged manually, so that the spans are updated and the table is repainted
        self.dataChanged.emit(None, None, None)

    def _get_category_insertion_index(self, category: Category | None) -> int:
        if category is None:
            for i in range(self.rowCount()):
                if self.item(i).data(501) == 'category':
                    return i
        else:
            for i in range(self.rowCount()):
                if self.item(i).data(501) == 'category' and self.item(i).data(502) == category.get_uid():
                    if i == self.rowCount() - 1:
                        return self.rowCount()
                    else:
                        for j in range(i + 1, self.rowCount()):
                            if self.item(j).data(501) == 'category':
                                return j
                        return self.rowCount()
        return -1

    def _get_category_start_index(self, category: Category | None) -> int:
        if category is None:
            return 0
        for i in range(self.rowCount()):
            if self.item(i).data(501) == 'category' and self.item(i).data(502) == category.get_uid():
                return i
        return -1

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

    def _move_row(self, workitem: Workitem, new_index: int, simple: bool = False):
        old_index = self._find_workitem(workitem)
        if old_index >= 0:  # It might be -1 for example if we hide completed items
            if not simple and new_index > old_index:
                new_index -= 1
            row = self.takeRow(old_index)
            self.insertRow(new_index, row)

    def _get_workitem_group(self, workitem: Workitem) -> Category | None:
        parent_category: Category = self.get_selected_category()
        if parent_category is not None:
            for existing in workitem.get_categories():
                if existing.get_parent() == parent_category:
                    return existing
        return None

    def _workitem_reordered(self, workitem: Workitem, new_index: int, carry: str, **kwargs) -> None:
        if (carry != 'ui' and
                type(self._backlog_or_tag) is Backlog and
                self._workitem_belongs_here(workitem)):

            logger.debug(f'Moving the row to {new_index} because workitem was reordered externally')

            visible_index: int = 0
            parent_category: Category = self.get_selected_category()
            if parent_category is None:
                # Only account for the hidden workitems
                for wi in workitem.get_parent().values():
                    if not self._hide_completed or not wi.is_sealed():
                        if wi == workitem:
                            break
                        visible_index += 1
            else:
                # Constraint it to current group
                group: Category | None = self._get_workitem_group(workitem)
                visible_index = self._get_category_start_index(group)
                for wi in workitem.get_parent().values():
                    if ((group is None and wi.is_uncategorized() or wi.has_category(group))
                            and (not self._hide_completed or not wi.is_sealed())):
                        visible_index += 1
                        if wi == workitem:
                            break

            logger.debug(f'Final visible index: {visible_index}')
            self._move_row(workitem, visible_index, True)

    def _workitem_category_changed(self, workitem: Workitem, added: set[Category], removed: set[Category], carry: str, **kwargs) -> None:
        if (carry != 'ui' and
                type(self._backlog_or_tag) is Backlog and
                self._workitem_belongs_here(workitem)):
            parent_category: Category = self.get_selected_category()
            if parent_category is not None:
                for c in added:
                    if c.get_parent() == parent_category:
                        new_index = self._get_category_insertion_index(c)
                        if new_index >= 0:
                            self._move_row(workitem, new_index)
                            return

                # We didn't add anything, so let's see if we need to remove instead
                for c in removed:
                    if c.get_parent() == parent_category:
                        new_index = self._get_category_insertion_index(None)
                        if new_index >= 0:
                            self._move_row(workitem, new_index)
                            return

    def _category_created(self, category: Category, **kwargs) -> None:
        if self._category_belongs_here(category):
            self._add_category(category)

    def _category_deleted(self, category: Category, **kwargs) -> None:
        if self._category_belongs_here(category):
            # Not the most efficient solution, but it will take care of reordering workitems correctly
            # It's a rare event anyway
            self.load(self._backlog_or_tag)
        elif self._selected_category_uid == category.get_uid():
            self._source_holder.get_settings().set({S.APPLICATION_SELECTED_CATEGORY: ''})

    def _category_renamed(self, category: Category, old_name: str, new_name: str, **kwargs) -> None:
        if self._category_belongs_here(category):
            self._category_changed(category)

    def _category_reordered(self, category: Category, new_index: int, carry: str, **kwargs) -> None:
        if self._category_belongs_here(category):
            # Not the most efficient solution, but it will take care of moving all child workitems correctly
            # It's a rare event anyway
            self.load(self._backlog_or_tag)

    def _workitem_moved(self, workitem: Workitem, old_backlog: Backlog, new_backlog: Backlog, **kwargs) -> None:
        if old_backlog == self._backlog_or_tag or self._backlog_or_tag.get_uid() in workitem.get_tags():
            # Moved from here
            self._remove_if_found(workitem)
        elif self._workitem_belongs_here(workitem):   # We can only drop workitems on backlogs, not tags
            # Moved in here
            self._add_workitem(workitem)

    def _workitem_changed(self, workitem: Workitem, **kwargs) -> None:
        for i in range(self.rowCount()):
            item0: WorkitemPlanned | CategoryItem = self.item(i, 0)
            if type(item0) is WorkitemPlanned:
                if item0.data(500) == workitem:
                    if self._hide_completed and workitem.is_sealed():
                        self.removeRow(i)
                    else:
                        font = self._get_font(workitem)
                        item0.update_font(font)
                        item0.update_planned()

                        item1: WorkitemTitle = self.item(i, 1)
                        item1.update_display()
                        item1.update_font(font)
                        item1.update_flags()

                        item2: WorkitemPomodoro = self.item(i, 2)
                        item2.update_display()
                    return

    def _category_changed(self, category: Category, **kwargs) -> None:
        for i in range(self.rowCount()):
            item0: WorkitemPlanned | CategoryItem = self.item(i, 0)
            if type(item0) is CategoryItem:
                if item0.data(502) == category.get_uid():
                    item0.update_display()
                    return

    def get_row_height(self):
        return self._row_height

    def get_selected_category(self) -> Category | None:
        if self._backlog_or_tag is None or type(self._backlog_or_tag) is Tag or not self._selected_category_uid:
            return None
        else:
            return self._backlog_or_tag.get_parent().find_category_by_id(self._selected_category_uid)

    def is_category_selected(self) -> bool:
        return self._selected_category_uid is not None and self._selected_category_uid != ''

    def group_by_category(self, workitems: list[Workitem], parent_category: Category) -> (dict[Category, list[Workitem]], list[Workitem]):
        res: dict[Category|None, list[Workitem]] = dict()
        uncategorized: list[Workitem] = list()
        cats = parent_category.values()

        for cat in cats:
            res[cat] = list()

        for w in workitems:
            found = False
            for cat in cats:
                if w.has_category(cat):
                    res[cat].append(w)
                    found = True
                    break
            if not found:
                uncategorized.append(w)

        return res, uncategorized

    def load(self, backlog_or_tag: Backlog | Tag) -> None:
        logger.debug(f'WorkitemModel.load({backlog_or_tag})')
        self.removeRows(0, self.rowCount())
        self._backlog_or_tag = backlog_or_tag
        if backlog_or_tag is not None:
            if type(backlog_or_tag) is Backlog:
                workitems = backlog_or_tag.values()
            else:
                workitems = sorted(backlog_or_tag.get_workitems(),
                                   key=lambda a: a.get_last_modified_date())

            parent_category: Category = self.get_selected_category()
            if parent_category is None:
                for workitem in workitems:
                    if self._hide_completed and workitem.is_sealed():
                        continue
                    self.appendRow(self.item_for_object(workitem))
            else:
                grouped, uncategorized = self.group_by_category(workitems, parent_category)

                # First add uncategorized items
                for workitem in uncategorized:
                    if not self._hide_completed or not workitem.is_sealed():
                        self.appendRow(self.item_for_object(workitem))

                # Then all categories below
                for category in grouped.keys():
                    self.appendRow(self.item_for_category(category))
                    for workitem in grouped[category]:
                        if not self._hide_completed or not workitem.is_sealed():
                            self.appendRow(self.item_for_object(workitem))

        self.data_loaded.emit()

    def hide_completed(self, hide: bool) -> None:
        self._hide_completed = hide
        self.load(self._backlog_or_tag)

    def get_backlog_or_tag(self) -> Backlog | Tag | None:
        return self._backlog_or_tag

    def get_primary_type(self) -> str:
        return 'application/flowkeeper.workitem.id'

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

    def item_for_category(self, category: Category) -> list[QStandardItem]:
        return [
            CategoryItem(category, self._font_category),
            StubItem(),
            StubItem(),
        ]

    def _get_category_for_index(self, raw_index: int) -> Category | None:
        for i in range(raw_index, -1, -1):
            item = self.item(i, 0)
            if isinstance(item, CategoryItem):
                return item.get_category()
        return None

    def _update_category(self, workitem: Workitem, raw_index: int) -> None:
        # This will be None if the user dragged the item to the top of the list, above all categories
        category: Category | None = self._get_category_for_index(raw_index)

        if category is not None and workitem.has_category(category):
            logger.debug(f'Already has category {category}, nothing to do')
            return

        to_add: str = category.get_uid() if category is not None else ''
        to_remove: set[str] = set()

        parent_category: Category = self.get_selected_category()
        for existing in workitem.get_categories():
            if existing.get_parent() == parent_category:
                to_remove.add(existing.get_uid())

        if len(to_remove) > 0 or len(to_add) > 0:
            logger.debug(f'Updating categories on workitem {workitem}: will remove "{";".join(to_remove)}", will add "{to_add}"')
            self._source_holder.get_source().execute(UpdateWorkitemCategoriesStrategy,
                                                     [workitem.get_uid(), ";".join(to_remove), to_add],
                                                     carry='ui')

    def reorder(self, to_index: int, raw_index: int, uid: str):
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
        logger.debug(f'When reordering {uid} having to add {to_add} items before our target index {to_index} (hide completed)')

        # Now skip the category headers, if categorization is enabled
        to_remove = 0
        if self.is_category_selected():
            for i in range(raw_index):
                if self.item(i).data(501) == 'category':
                    to_remove += 1
        logger.debug(f'When reordering {uid} having to remove {to_remove} items before our target index {to_index} (category headers)')

        # First update category, then reorder. This will help us to constraint reordering to the same category.
        self._update_category(self._backlog_or_tag[uid], raw_index)

        self._source_holder.get_source().execute(ReorderWorkitemStrategy,
                                                 [uid, str(to_index + to_add - to_remove)],
                                                 carry='ui')

    def repaint_workitem(self, workitem: Workitem):
        for i in range(self.rowCount()):
            wi = self.item(i).data(500)  # 500 ~ Qt.UserRole + 1
            if wi == workitem:
                item: WorkitemPomodoro = self.item(i, 2)
                item.update_display()

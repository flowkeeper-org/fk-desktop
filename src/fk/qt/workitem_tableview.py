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

from PySide6.QtCore import Qt, QModelIndex, QPoint, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource, start_workitem
from fk.core.abstract_settings import S
from fk.core.backlog import Backlog
from fk.core.category import Category
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemCreate, AfterSettingsChanged, AfterWorkitemCategoryChange
from fk.core.pomodoro import POMODORO_TYPE_NORMAL, Pomodoro, POMODORO_TYPE_TRACKER
from fk.core.pomodoro_strategies import AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.tag import Tag
from fk.core.timer import PomodoroTimer
from fk.core.timer_data import TimerData
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, RestoreWorkitemStrategy, \
    UpdateWorkitemCategoriesStrategy
from fk.desktop.application import Application
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.actions import Actions
from fk.qt.focus_widget import complete_item
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.workitem_model import WorkitemModel
from fk.qt.workitem_state_delegate import WorkitemStateDelegate
from fk.qt.workitem_text_delegate import WorkitemTextDelegate

logger = logging.getLogger(__name__)


class WorkitemTableView(AbstractTableView[Backlog | Tag, Workitem]):
    _application: Application
    _menu: QMenu

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 source_holder: EventSourceHolder,
                 timer: PomodoroTimer | None,
                 actions: Actions):
        super().__init__(parent,
                         source_holder,
                         WorkitemModel(parent, source_holder),
                         'workitems_table',
                         actions,
                         'Loading, please wait...',
                         '← Select a backlog or tag.',
                         'The selected backlog is empty.\nCreate the first workitem by pressing Ins key.',
                         1)
        self._application = application
        self._configure_delegate()
        self._menu = self._init_menu(actions)
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self.update_actions(None)
        application.get_settings().on(AfterSettingsChanged, self._on_setting_changed)
        if timer is not None:
            timer.on(PomodoroTimer.TimerTick, self._on_tick)
        else:
            logger.debug('WorkitemTableView will not update automatically on timer ticks')

        self.model().data_loaded.connect(self._create_category_spans)

        # Set resizing policy
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().resizeSection(0, 16)
        self._vertical_resizing()

    def _create_category_spans(self):
        self.clearSpans()
        if self.model().is_category_selected():
            # Create spans for categories
            model = self.model()
            for i in range(model.rowCount()):
                index = model.index(i, 0)
                if index.data(501) == 'category':
                    self.setSpan(i, 0, 1, 3)
            self.horizontalHeader().resizeSections()

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if S.APPLICATION_THEME in new_values or S.APPLICATION_FEATURE_TAGS in new_values:
            self._configure_delegate()
            self._vertical_resizing()

    def _is_tags_enabled(self) -> bool:
        return self._application.get_settings().get(S.APPLICATION_FEATURE_TAGS) == 'True'

    def _configure_delegate(self):
        # Workitem state -- image or no delegate
        if self._is_tags_enabled():
            self.setItemDelegateForColumn(
                0,
                WorkitemStateDelegate(
                    self,
                    self._application.get_icon_theme(),
                    self._application.get_theme_variables()['TABLE_TEXT_COLOR'],
                    self._application.get_theme_variables()['SELECTION_BG_COLOR'],
                    self._application.get_theme_variables()['TABLE_CROSSOUT_COLOR']))
        else:
            self.setItemDelegateForColumn(0, None)

        # Workitem text -- HTML or no delegate
        if self._is_tags_enabled():
            self.setItemDelegateForColumn(
                1,
                WorkitemTextDelegate(
                    self,
                    self._application.get_icon_theme(),
                    self._application.get_theme_variables()['TABLE_TEXT_COLOR'],
                    self._application.get_theme_variables()['SELECTION_BG_COLOR'],
                    self._application.get_theme_variables()['TABLE_CROSSOUT_COLOR']))
        else:
            self.setItemDelegateForColumn(1, None)

        # Pomodoros display
        self.setItemDelegateForColumn(
            2,
            PomodoroDelegate(
                self,
                self._application.get_icon_theme(),
                self._application.get_theme_variables()['SELECTION_BG_COLOR'],
                self._application.get_theme_variables()['TABLE_CROSSOUT_COLOR'],
                self._is_tags_enabled()))

    def _update_actions_if_needed(self, workitem: Workitem):
        current = self.get_current()
        if workitem == current:
            self.update_actions(current)

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        super()._on_source_changed(event, source)
        source.on(AfterWorkitemCreate, self._on_new_workitem)
        source.on(AfterWorkitemCategoryChange, self._on_new_workitem)   # This will edit it, too
        source.on("AfterWorkitem*",
                  lambda workitem, **kwargs: self._update_actions_if_needed(workitem))
        source.on('AfterPomodoro*',
                  lambda **kwargs: self._update_actions_if_needed(
                      kwargs['workitem'] if 'workitem' in kwargs else kwargs['pomodoro'].get_parent()
                  ))
        source.on('Timer(Work|Rest)(Start|Complete)', lambda **_: self.update_actions(self.get_current()))
        self.selectionModel().clear()
        self.upstream_selected(None)

    def _init_menu(self, actions: Actions) -> QMenu:
        menu: QMenu = QMenu()
        menu.addActions([
            actions['workitems_table.newItem'],
            actions['workitems_table.renameItem'],
            actions['workitems_table.deleteItem'],
            actions['workitems_table.startItem'],
            actions['workitems_table.addPomodoro'],
            actions['workitems_table.removePomodoro'],
            actions['workitems_table.hideCompleted'],
            actions['workitems_table.completeItem'],
            actions['workitems_table.restoreItem'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))
        return menu

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('workitems_table.newItem', "New Item", 'Ins', "tool-add", WorkitemTableView.create_workitem)
        actions.add('workitems_table.renameItem', "Rename Item", 'F6', "tool-rename", WorkitemTableView.rename_selected_workitem)
        actions.add('workitems_table.deleteItem', "Delete Item", 'Del', "tool-delete", WorkitemTableView.delete_selected_workitem)
        actions.add('workitems_table.startItem', "Start Item", 'Ctrl+S', "tool-start-item", WorkitemTableView.start_selected_workitem)
        actions.add('workitems_table.completeItem', "Complete Item", 'Ctrl+P', "tool-complete-item", WorkitemTableView.complete_selected_workitem)
        actions.add('workitems_table.restoreItem', "Undo Completion", 'Ctrl+P', "tool-restore-item", WorkitemTableView.restore_selected_workitem)
        actions.add('workitems_table.addPomodoro', "Add Pomodoro", 'Ctrl++', "tool-add-pomodoro", WorkitemTableView.add_pomodoro)
        actions.add('workitems_table.removePomodoro', "Remove Pomodoro", 'Ctrl+-', "tool-remove-pomodoro", WorkitemTableView.remove_pomodoro)
        actions.add('workitems_table.hideCompleted',
                    "Hide Completed Items",
                    '',
                    ("tool-filter-on", "tool-filter-off"),
                    WorkitemTableView._toggle_hide_completed_workitems,
                    True,
                    actions.get_settings().get(S.APPLICATION_HIDE_COMPLETED) == 'True')

    def upstream_selected(self, backlog_or_tag: Backlog | Tag | None) -> None:
        super().upstream_selected(backlog_or_tag)
        is_backlog = type(backlog_or_tag) is Backlog
        self._actions['workitems_table.newItem'].setEnabled(is_backlog)
        self._create_category_spans()

    def _enable_action(self, name: str, is_enabled: bool) -> None:
        self._actions[name].setEnabled(is_enabled)
        self._actions[name].setVisible(is_enabled)

    def update_actions(self, selected: Workitem | None) -> None:
        # It can be None for example if we don't have any backlogs left, or if we haven't loaded any yet.
        is_workitem_selected = selected is not None
        is_workitem_editable = is_workitem_selected and not selected.is_sealed()
        is_workitem_sealed = is_workitem_selected and selected.is_sealed()
        is_tracker = is_workitem_selected and selected.is_tracker()
        self._enable_action('workitems_table.deleteItem', is_workitem_selected)
        self._enable_action('workitems_table.renameItem', is_workitem_editable)
        self._enable_action('workitems_table.completeItem', is_workitem_editable)
        self._enable_action('workitems_table.restoreItem', is_workitem_sealed)
        self._enable_action('workitems_table.addPomodoro', is_workitem_editable and not is_tracker)
        self._enable_action('workitems_table.removePomodoro', is_workitem_editable
                                                                   and selected.is_startable()
                                                                   and not is_tracker)
        self._enable_action('workitems_table.startItem', is_workitem_editable
                                                              and (selected.is_startable() or len(selected) == 0 or selected.is_tracker())
                                                              and self._source.get_data().get_current_user().get_timer().is_idling())

    # Actions

    def get_category_for_new_item(self) -> str | None:
        default_category: str = self._source.get_settings().get(S.APPLICATION_DEFAULT_WORKITEM_CATEGORY)
        if default_category == 'ask':
            parent_category: Category|None = self.model().get_selected_category()
            if parent_category is not None:
                context_menu = QMenu(self)
                for i, child in enumerate(parent_category.values()):
                    action = QAction(f'&{i + 1} {child.get_short_name()}', self)
                    action.setData(child.get_uid())
                    context_menu.addAction(action)
                context_menu.show() # To get correct size on the next line
                menu_size: QSize = context_menu.geometry().size()
                my_center: QPoint = self.geometry().center()
                my_center.setX(int(my_center.x() - menu_size.width() / 2))
                my_center.setY(int(my_center.y() - menu_size.height() / 2))
                selected: QAction = context_menu.exec(self.parent().mapToGlobal(my_center))
                if selected is not None:
                    return selected.data()
        elif default_category == 'none':
            return None
        else:
            return default_category

    def create_workitem(self) -> None:
        model = self.model()
        backlog_or_tag: Backlog | Tag = model.get_backlog_or_tag()
        if backlog_or_tag is None:
            raise Exception("Trying to create a workitem while there's no backlog nor tag selected")
        if type(backlog_or_tag) is Tag:
            raise Exception("Trying to create a workitem directly in a tag -- shouldn't be possible")

        category_uid = self.get_category_for_new_item()

        backlog: Backlog = backlog_or_tag
        new_name = generate_unique_name("Do something", backlog.names())
        new_uid = generate_uid()
        will_move = category_uid is not None

        self._source.execute(CreateWorkitemStrategy,
                             [new_uid, backlog.get_uid(), new_name],
                             carry=None if will_move else "edit")   # We'll edit after moving to another category

        if will_move:
            self._source.execute(UpdateWorkitemCategoriesStrategy,
                                 [new_uid, '', category_uid],
                                 carry="edit")

        # A simpler, more efficient, but a bit uglier single-step alternative
        # (new_name, ok) = QInputDialog.getText(self,
        #                                       "New item",
        #                                       "Provide a name for the new item",
        #                                       text="Do something")
        # if ok:
        #     self._source.execute(CreateWorkitemStrategy, [generate_uid(), backlog.get_uid(), new_name])

    def _on_new_workitem(self, workitem: Workitem, **kwargs):
        if 'carry' in kwargs and kwargs['carry'] == 'edit':
            index: QModelIndex = self.select(workitem)
            self.edit(index)

    def rename_selected_workitem(self) -> None:
        index: QModelIndex = self.currentIndex()
        if index is None:
            raise Exception("Trying to rename a workitem, while there's none selected")
        self.edit(index)

    def delete_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to delete a workitem, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete workitem '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteWorkitemStrategy, [selected.get_uid()])

    def start_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to start a workitem, while there's none selected")
        start_workitem(selected, self._source)

    def complete_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        complete_item(selected, self, self._source)

    def restore_selected_workitem(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to restore a workitem, while there's none selected")
        if selected.is_sealed():
            self._source.execute(RestoreWorkitemStrategy, [selected.get_uid()])

    def add_pomodoro(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to add pomodoro to a workitem, while there's none selected")
        self._source.execute(AddPomodoroStrategy, [
            selected.get_uid(),
            "1",
            POMODORO_TYPE_NORMAL
        ])

    def remove_pomodoro(self) -> None:
        selected: Workitem = self.get_current()
        if selected is None:
            raise Exception("Trying to remove pomodoro from a workitem, while there's none selected")
        self._source.execute(RemovePomodoroStrategy, [
            selected.get_uid(),
            "1"
        ])

    def _toggle_hide_completed_workitems(self, checked: bool) -> None:
        self.model().hide_completed(checked)
        self._source.set_config_parameters({S.APPLICATION_HIDE_COMPLETED: str(checked)})

    def _vertical_resizing(self) -> None:
        # Resizing to contents results in visible blinking on Kubuntu 20.04, so cannot be enabled by default.
        self.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents if self._is_tags_enabled() else QHeaderView.ResizeMode.Fixed)

    def _on_tick(self, timer: TimerData, counter: int, event: str) -> None:
        if counter % 10 == 0:
            pomodoro: Pomodoro = timer.get_running_pomodoro()
            # We only care about repainting workitems in tracking mode
            if pomodoro is not None and pomodoro.get_type() == POMODORO_TYPE_TRACKER:
                workitem: Workitem = pomodoro.get_parent()
                backlog: Backlog = workitem.get_parent()
                if backlog == self.model().get_backlog_or_tag():
                    self.model().repaint_workitem(workitem)

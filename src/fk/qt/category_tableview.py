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

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QWidget, QHeaderView, QMenu, QMessageBox, QInputDialog

from fk.core import events
from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.category import Category
from fk.core.category_strategies import CreateCategoryStrategy, DeleteCategoryStrategy
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterCategoryCreate, SourceMessagesProcessed
from fk.core.user import User
from fk.qt.abstract_tableview import AbstractTableView
from fk.qt.actions import Actions
from fk.qt.category_model import CategoryModel

logger = logging.getLogger(__name__)


class CategoryTableView(AbstractTableView[User, Category]):
    _application: 'Application'
    _menu: QMenu
    _root_category_id: str

    def __init__(self,
                 parent: QWidget,
                 application: 'Application',
                 source_holder: EventSourceHolder,
                 actions: Actions,
                 root_category_id: str):
        super().__init__(parent,
                         source_holder,
                         CategoryModel(parent, source_holder),
                         'categories_table',
                         actions,
                         'Loading, please wait...',
                         'No data or connection error.',
                         "You haven't got any categories yet. Create the first one by pressing Ctrl+N.",
                         0)
        self._root_category_id = root_category_id
        self._menu = self._init_menu(actions)
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        self._application = application
        self.update_actions(None)
        if source_holder.get_source() is not None:
            self._on_source_changed(None, source_holder.get_source())
            self._on_messages(None, source_holder.get_source())
            self._on_data_loaded(None, source_holder.get_source())
            self._unlock_ui(None, 0)

    def _lock_ui(self, event, after: int, last_received: datetime.datetime) -> None:
        self.update_actions(self.get_current())

    def _unlock_ui(self, event, ping: int) -> None:
        self.update_actions(self.get_current())

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        super()._on_source_changed(event, source)
        self.selectionModel().clear()
        self.upstream_selected(None)
        print('_on_source_changed')
        source.on(AfterCategoryCreate, self._on_new_category)
        source.on(SourceMessagesProcessed, self._on_messages)

        source.on("AfterCategory*",
                  lambda category, **kwargs: self._update_actions_if_needed(category))

        heartbeat = self._application.get_heartbeat()
        heartbeat.on(events.WentOffline, self._lock_ui)
        heartbeat.on(events.WentOnline, self._unlock_ui)

    def _init_menu(self, actions: Actions) -> QMenu:
        menu: QMenu = QMenu()
        menu.addActions([
            actions['categories_table.openSubCategory'],
            actions['categories_table.newCategory'],
            actions['categories_table.renameCategory'],
            actions['categories_table.deleteCategory'],
            actions['categories_table.openParentCategory'],
            # Uncomment to troubleshoot
            # actions['categories_table.dumpCategory'],
        ])
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda p: menu.exec(self.mapToGlobal(p)))
        return menu

    def upstream_selected(self, category: Category) -> None:
        super().upstream_selected(category)
        print(f'Upstream selected {category}')
        self._actions['categories_table.newCategory'].setEnabled(category is not None)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        # Auto-select the first subcategory, if any
        if category is not None:
            to_select: Category = category.first()
            if to_select is not None:
                self.select(to_select)

            # If we want to do commander-like navigation
            # self.select(None)

    def _update_actions_if_needed(self, category: Category):
        if category is not None:
            current = self.get_current()
            if category == current:
                self.update_actions(current)

    def update_actions(self, selected: Category) -> None:
        logger.debug(f'Category table - update_actions({selected})')
        # It can be None for example if we don't have any categories left, or if
        # we haven't loaded any yet. CategoryModel supports None.
        is_category_selected = selected is not None

        heartbeat = self._application.get_heartbeat()
        source = self._application.get_source_holder().get_source()
        is_online = heartbeat.is_online() or source is None or not source.can_connect()
        parent_category: Category = self.model().get_parent_category()
        logger.debug(f' - Online: {is_online}')
        logger.debug(f' - Category selected: {is_category_selected}')
        logger.debug(f' - Heartbeat: {heartbeat}')

        def set_active(name: str, state: bool) -> None:
            self._actions[name].setEnabled(state)
            self._actions[name].setVisible(state)

        set_active('categories_table.newCategory', is_online)
        set_active('categories_table.renameCategory', is_category_selected and is_online)
        set_active('categories_table.deleteCategory', is_category_selected and is_online)
        set_active('categories_table.openSubCategory', is_category_selected)
        set_active('categories_table.openParentCategory', parent_category is not None and not parent_category.is_root())
        set_active('categories_table.dumpCategory', is_category_selected)

        # TODO: Double-clicking the category name doesn't use those

    def _on_new_category(self, category: Category, carry: any = None, **kwargs):
        if carry == 'edit':
            index: QModelIndex = self.select(category)
            self.edit(index)
        elif carry == 'select':
            self.select(category)

    def _on_messages(self, event: str, source: AbstractEventSource) -> None:
        user = source.get_data().get_current_user()
        self.upstream_selected(user.find_category_by_id(self._root_category_id))

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('categories_table.newCategory',
                    "New Category",
                    'Ctrl+N',
                    "tool-add",
                    CategoryTableView.create_category)
        actions.add('categories_table.renameCategory',
                    "Rename Category",
                    'Ctrl+R',
                    "tool-rename",
                    CategoryTableView.rename_selected_category)
        actions.add('categories_table.deleteCategory',
                    "Delete Category",
                    'F8',
                    "tool-delete",
                    CategoryTableView.delete_selected_category)
        actions.add('categories_table.dumpCategory',
                    "Dump (DEBUG)",
                    'Ctrl+D',
                    None,
                    CategoryTableView.dump_selected_category)
        actions.add('categories_table.openSubCategory',
                    "Open",
                    'Right',
                    "tool-forward",
                    CategoryTableView.open_selected_category)
        actions.add('categories_table.openParentCategory',
                    "Back",
                    'Left',
                    "tool-back",
                    CategoryTableView.open_parent_category)

    # Actions

    def create_category(self) -> str:
        parent: Category = self.model().get_parent_category()
        if parent is None:
            raise Exception('Trying to create a category without a parent')
        names = [c.get_name() for c in parent.values()]
        new_name = generate_unique_name('Category', names)
        new_uid = generate_uid()
        self._source.execute(CreateCategoryStrategy, [new_uid, parent.get_uid(), new_name], carry='edit')
        return new_uid

    def rename_selected_category(self) -> None:
        index: QModelIndex = self.currentIndex()
        if index is None:
            raise Exception("Trying to rename a category, while there's none selected")
        self.edit(index)

    def delete_selected_category(self) -> None:
        selected: Category = self.get_current()
        if selected is None:
            raise Exception("Trying to delete a category, while there's none selected")
        if QMessageBox().warning(self,
                                 "Confirmation",
                                 f"Are you sure you want to delete category '{selected.get_name()}'?",
                                 QMessageBox.StandardButton.Ok,
                                 QMessageBox.StandardButton.Cancel
                                 ) == QMessageBox.StandardButton.Ok:
            self._source.execute(DeleteCategoryStrategy, [selected.get_uid()])

    def open_selected_category(self) -> None:
        selected: Category = self.get_current()
        if selected is None:
            index = self.currentIndex()
            if index is not None:
                if index.data(502):
                    self.open_parent_category()
                    return
            raise Exception("Trying to open a category, while there's none selected")
        self.upstream_selected(selected)

    def open_parent_category(self) -> None:
        current: Category = self.model().get_parent_category()
        if current is None:
            raise Exception("No category loaded")
        parent = current.get_parent()
        if parent is None or not isinstance(parent, Category):
            raise Exception("Trying to open parent category, while we are already at the root")
        self.upstream_selected(parent)
        self.select(current)

    def dump_selected_category(self) -> None:
        selected: Category = self.get_current()
        if selected is None:
            raise Exception("Trying to dump a category, while there's none selected")
        QInputDialog.getMultiLineText(None,
                                      "Category dump",
                                      "Technical information for debug / development purposes",
                                      selected.dump())

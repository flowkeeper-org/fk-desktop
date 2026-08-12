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
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout

from fk.core.category import Category
from fk.core.event_source_holder import EventSourceHolder
from fk.qt.ElidedLabel import ElidedLabel
from fk.qt.abstract_tableview import AfterUpstreamSelected
from fk.qt.actions import Actions
from fk.qt.category_tableview import CategoryTableView
from fk.qt.configurable_toolbar import ConfigurableToolBar


class CategoryWidget(QWidget):
    _category_table: CategoryTableView
    _breadcrumbs: ElidedLabel
    _source_holder: EventSourceHolder
    _max_depth: int

    def __init__(self,
                 parent: QWidget,
                 application: 'Application',
                 source_holder: EventSourceHolder,
                 actions: Actions,
                 root_category_id: str,
                 max_depth: int):
        super().__init__(parent)
        self.setObjectName('categories_widget')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self._source_holder = source_holder
        self._max_depth = max_depth
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        tb = ConfigurableToolBar(self, actions, "categories_toolbar")
        tb.addAction(actions['categories_table.newCategory'])
        tb.addAction(actions['categories_table.deleteCategory'])
        tb.addAction(actions['categories_table.renameCategory'])
        tb.addAction(actions['categories_table.openParentCategory'])
        tb.addAction(actions['categories_table.openSubCategory'])
        layout.addWidget(tb)

        self._breadcrumbs = ElidedLabel(self)
        self._breadcrumbs.setObjectName('categories_breadcrumbs')
        layout.addWidget(self._breadcrumbs)

        self._category_table = CategoryTableView(self, application, source_holder, actions, root_category_id, self._max_depth)
        self._category_table.on(AfterUpstreamSelected, self._update_breadcrumbs)
        layout.addWidget(self._category_table)

        current: Category = self._category_table.model().get_parent_category()
        if current is not None:
            self._update_breadcrumbs(None, current)

    def get_table(self) -> CategoryTableView:
        return self._category_table

    def _update_breadcrumbs(self, event: str, upstream: Category) -> None:
        if upstream is None:
            self._breadcrumbs.setText('N/A')
        else:
            tokens = []
            while not upstream.is_root():
                tokens.append(upstream.get_name())
                upstream = upstream.get_parent()
            tokens.append('All')
            self._breadcrumbs.setText(' > '.join(reversed(tokens)))

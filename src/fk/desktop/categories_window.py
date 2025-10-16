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

from PySide6 import QtUiTools, QtWidgets
from PySide6.QtCore import QObject, QFile
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder
from fk.qt.abstract_tableview import AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.category_widget import CategoryWidget


class CategoriesWindow(QObject):
    _source: AbstractEventSource
    _categories_window: QMainWindow
    _data: dict[datetime.date, dict[str, list[datetime.timedelta, set[str]]]]

    def __init__(self,
                 parent: QWidget,
                 source_holder: EventSourceHolder,
                 app: 'Application',
                 actions: Actions):
        super().__init__(parent)
        self._source = source_holder.get_source()

        file = QFile(":/categories.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._categories_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

        layout: QHBoxLayout = self._categories_window.findChild(QtWidgets.QHBoxLayout, "layout")

        categories_table_left: CategoryWidget = CategoryWidget(
            self._categories_window,
            app,
            source_holder,
            actions,
            '#workitem_groups')
        actions.bind('categories_table', categories_table_left.get_table())
        layout.addWidget(categories_table_left)

        # categories_table_right: CategoryWidget = CategoryWidget(
        #     self._categories_window,
        #     app,
        #     source_holder,
        #     actions,
        #     '')
        # # actions.bind('categories_table_right', categories_table_right)
        # layout.addWidget(categories_table_right)

        # categories_table_left.get_table().on(
        #     AfterSelectionChanged,
        #     lambda event, before, after: categories_table_right.get_table().upstream_selected(after))

        close_action = QAction(self._categories_window, 'Close')
        close_action.triggered.connect(self._categories_window.close)
        close_action.setShortcut('Esc')
        self._categories_window.addAction(close_action)

    def show(self):
        self._categories_window.show()

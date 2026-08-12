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
from PySide6.QtGui import QAction, Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QSizePolicy, QSplitter, QScrollArea

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.category import Category
from fk.core.event_source_holder import EventSourceHolder
from fk.qt.abstract_tableview import AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.category_tableview import CategoryTableView
from fk.qt.category_widget import CategoryWidget


class CategoriesWindow(QObject):
    _source: AbstractEventSource
    _categories_window: QMainWindow
    _category_info: QLabel
    _scroll_area: QScrollArea
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

        splitter = QSplitter(self._categories_window)
        layout.addWidget(splitter)

        categories_table: CategoryWidget = CategoryWidget(
            self._categories_window,
            app,
            source_holder,
            actions,
            '#workitem_groups',
            1)
        actions.bind('categories_table', categories_table.get_table())
        # TODO: Enable actions. Disable by default, and every time the window is closed.
        splitter.addWidget(categories_table)

        splitter.addWidget(self._configure_info_view(categories_table.get_table()))
        splitter.setSizes([250, 450])

        close_action = QAction(self._categories_window, 'Close')
        close_action.triggered.connect(self._categories_window.close)
        close_action.setShortcut('Esc')
        self._categories_window.addAction(close_action)

    def _configure_info_view(self, categories_table_view: CategoryTableView) -> QWidget:
        description = QLabel(categories_table_view)
        description.setObjectName('categories_info')
        description.setTextFormat(Qt.TextFormat.MarkdownText)
        description.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.TextBrowserInteraction)
        description.setWordWrap(True)
        description.setOpenExternalLinks(True)
        description.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._category_info = description

        scroll = QScrollArea(self._categories_window)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(description)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('border: none;')
        self._scroll_area = scroll

        categories_table_view.on(AfterSelectionChanged, lambda after, **_: self._display_category_info(after))
        self._display_category_info(categories_table_view.get_current())

        return scroll

    def _display_category_info(self, category: Category):
        if category is None or category.get_info() is None or category.get_info() == '':
            self._category_info.setText('N/A')
        else:
            self._category_info.setText(category.get_info())

        # Reset the scroll
        self._scroll_area.verticalScrollBar().setValue(0)
        self._scroll_area.horizontalScrollBar().setValue(0)

    def show(self):
        self._categories_window.show()

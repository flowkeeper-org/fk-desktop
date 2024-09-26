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
from typing import Collection

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import TagCreated, TagDeleted, SourceMessagesProcessed
from fk.core.tag import Tag
from fk.desktop.application import Application, AfterSourceChanged
from fk.qt.flow_layout import FlowLayout

logger = logging.getLogger(__name__)


class TagsWidget(QWidget):
    _application: Application
    _source: AbstractEventSource
    _layout: FlowLayout

    def __init__(self, parent: QWidget, application: Application):
        super().__init__(parent)
        self._application = application
        self._source = None
        self.setObjectName('tags')
        self.setContentsMargins(10, 0, 10, 10)

        self._layout = FlowLayout(self)
        self._layout.setObjectName(f"tags_layout")
        self.setLayout(self._layout)

        application.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def _add_tag(self, tag: Tag, event: str = None) -> None:
        widget = QLabel(f'#{tag.get_uid()}', self)
        widget.setObjectName(f'tag-label')
        self._layout.addWidget(widget)

    def _delete_tag(self, tag: Tag, event: str) -> None:
        for widget in self._get_child_widgets():
            if widget.text() == f'#{tag.get_uid()}':
                self._layout.removeWidget(widget)
                widget.deleteLater()
                break

    def _init_tags(self, source: AbstractEventSource, event: str = None) -> None:
        for widget in self._get_child_widgets():
            self.children().remove(widget)
        for tag in source.get_data().get_current_user().get_tags().values():
            self._add_tag(tag)

    def _get_child_widgets(self) -> Collection[QLabel]:
        res = list[QWidget]()
        for widget in self.children():
            if widget.objectName().startswith('tag-'):
                res.append(widget)
        return res

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._source = source
        source.on(TagCreated, self._add_tag)
        source.on(TagDeleted, self._delete_tag)
        source.on(SourceMessagesProcessed, self._init_tags)

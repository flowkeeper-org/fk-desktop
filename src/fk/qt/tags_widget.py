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

from PySide6.QtWidgets import QWidget, QFrame, QPushButton

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import TagCreated, TagDeleted, SourceMessagesProcessed
from fk.core.tag import Tag
from fk.desktop.application import Application, AfterSourceChanged
from fk.qt.abstract_tableview import BeforeSelectionChanged, AfterSelectionChanged
from fk.qt.flow_layout import FlowLayout

logger = logging.getLogger(__name__)


class TagsWidget(QFrame, AbstractEventEmitter):
    _application: Application
    _source: AbstractEventSource

    def __init__(self, parent: QWidget, application: Application):
        super().__init__(parent,
                         allowed_events=[
                             BeforeSelectionChanged,
                             AfterSelectionChanged,
                         ],
                         callback_invoker=application.get_settings().invoke_callback)
        self._application = application
        self._source = None

        self.setObjectName('tags_table')
        self.setLayout(FlowLayout(self))

        application.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def _add_tag(self, tag: Tag, event: str = None, carry: any = None) -> None:
        widget = QPushButton(f'#{tag.get_uid()}', self)
        widget.setObjectName(tag.get_uid())
        widget.setProperty('class', 'tag_label')
        widget.setCheckable(True)
        widget.toggled.connect(lambda is_checked: self._on_tag_toggled(widget, is_checked, tag))
        self.layout().addWidget(widget)

    def get_selection(self) -> str | None:
        for w in self.layout().widgets():
            if type(w) is QPushButton and w.isChecked():
                return w.objectName()
        return None

    def deselect(self) -> None:
        for w in self.layout().widgets():
            if type(w) is QPushButton and w.isChecked():
                w.blockSignals(True)
                w.setChecked(False)
                w.blockSignals(False)

    def _on_tag_toggled(self, widget: QPushButton, is_checked: bool, tag: Tag) -> None:
        if is_checked:
            # We selected a tag -- see if we need to deselect anything else
            before = None
            for w in self.layout().widgets():
                if type(w) is QPushButton and w != widget and w.isChecked():
                    before = self._find_tag(w.objectName())
                    break

            params = {
                'before': before,
                'after': self._find_tag(tag.get_uid()),
            }
            self._emit(BeforeSelectionChanged, params)
            w.blockSignals(True)
            w.setChecked(False)
            w.blockSignals(False)
            self._emit(AfterSelectionChanged, params)
        else:
            # We deselected a tag
            params = {
                'before': self._find_tag(tag.get_uid()),
                'after': None,
            }
            self._emit(BeforeSelectionChanged, params)
            self._emit(AfterSelectionChanged, params)

    def _delete_tag(self, tag: Tag, event: str, carry: any = None) -> None:
        for widget in self.layout().widgets():
            if widget.objectName() == tag.get_uid():
                if widget.isChecked():
                    # The tag was selected -- deselect it and fire events properly
                    params = {
                        'before': self._find_tag(tag.get_uid()),
                        'after': None,
                    }
                    self._emit(BeforeSelectionChanged, params)
                    widget.setChecked(False)
                    self._emit(AfterSelectionChanged, params)
                self.layout().removeWidget(widget)
                widget.deleteLater()
                break

    def _find_tag(self, uid: str) -> Tag:
        return self._source.find_tag(uid)

    def _init_tags(self, source: AbstractEventSource, event: str = None) -> None:
        for widget in self.layout().widgets():
            self.layout().removeWidget(widget)
            widget.deleteLater()
        for tag in source.get_data().get_current_user().get_tags().values():
            self._add_tag(tag)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._source = source
        source.on(TagCreated, self._add_tag)
        source.on(TagDeleted, self._delete_tag)
        source.on(SourceMessagesProcessed, self._init_tags)

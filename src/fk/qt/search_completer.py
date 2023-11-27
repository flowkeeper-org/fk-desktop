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

from PySide6 import QtWidgets, QtGui, QtCore

from fk.core.abstract_event_source import AbstractEventSource


class SearchBar(QtWidgets.QLineEdit):
    _source: AbstractEventSource

    def __init__(self, parent: QtWidgets.QWidget, source: AbstractEventSource):
        super().__init__(parent)
        self.setObjectName("search")
        self._source = source
        self.hide()
        self.setPlaceholderText('Search')
        self.returnPressed.connect(lambda: self.search())
        self.installEventFilter(self)

    def show(self) -> None:
        completer = QtWidgets.QCompleter([wi.get_name() for wi in self._source.workitems()])
        completer.setFilterMode(QtGui.Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(QtGui.Qt.CaseSensitivity.CaseInsensitive)
        self.setCompleter(completer)
        self.setFocus()
        if not self.isVisible():
            self.setText("")
        super().show()

    def search(self) -> None:
        text: str = self.text().lower()
        if len(text) > 0:
            for wi in self._source.workitems():
                if wi.get_name().lower() == text:
                    # TODO: Implement this selection
                    print(f'Will select workitem {wi}')
                    self.hide()
        else:
            self.hide()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if widget == self and event.type() == QtCore.QEvent.Type.KeyPress and isinstance(event, QtGui.QKeyEvent):
            if event.matches(QtGui.QKeySequence.StandardKey.Cancel):
                self.hide()
        return False

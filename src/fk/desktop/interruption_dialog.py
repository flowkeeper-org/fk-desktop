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

from PySide6.QtGui import QHideEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QDialog, QDialogButtonBox, QLineEdit

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import AfterPomodoroComplete

logger = logging.getLogger(__name__)


class InterruptionDialog(QDialog):
    _source: AbstractEventSource
    _warning: QLabel
    _reason: QLineEdit
    _buttons: QDialogButtonBox

    def __init__(self,
                 parent: QWidget,
                 source: AbstractEventSource,
                 window_title: str,
                 label_text: str,
                 placeholder_text: str):
        super().__init__(parent)
        self._source = source

        self.setWindowTitle(window_title)

        layout = QVBoxLayout(self)

        label = QLabel(label_text, self)
        layout.addWidget(label)

        self._reason = QLineEdit(self)
        self._reason.setPlaceholderText(placeholder_text)
        layout.addWidget(self._reason)

        self._warning = QLabel('Too late, the pomodoro has just finished.', self)
        self._warning.setObjectName('warning')
        self._warning.setVisible(False)
        layout.addWidget(self._warning)

        self._buttons = QDialogButtonBox(self)
        self._buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.clicked.connect(lambda btn: self._on_action(self._buttons.buttonRole(btn)))
        layout.addWidget(self._buttons)

        self._source.on(AfterPomodoroComplete, self._on_pomodoro_complete)
        logger.debug('Subscribed to AfterPomodoroComplete')

    def hideEvent(self, event: QHideEvent) -> None:
        self._source.unsubscribe(self._on_pomodoro_complete)
        logger.debug('Unsubscribed from AfterPomodoroComplete')
        super(InterruptionDialog, self).hideEvent(event)

    def _on_pomodoro_complete(self, **_) -> None:
        logger.debug('Received AfterPomodoroComplete')
        self._warning.setVisible(True)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _on_action(self, role: QDialogButtonBox.ButtonRole):
        logger.debug(f'Closing Interruption dialog with role {role}')

        if role == QDialogButtonBox.ButtonRole.AcceptRole:
            self.accept()
        else:
            self.reject()

    def get_reason(self) -> str:
        return self._reason.text()

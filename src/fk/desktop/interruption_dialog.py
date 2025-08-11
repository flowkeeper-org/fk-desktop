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

from PySide6.QtGui import QHideEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QDialog, QTextEdit, \
    QDialogButtonBox

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import AfterPomodoroComplete


# TODO Add logs
# TODO Void / interrupt
# TODO Better text for the warning
# TODO Fix text based on "void" param
# TODO Smaller reason edit

class InterruptionDialog(QDialog):
    _source: AbstractEventSource
    _void: bool
    _warning: QLabel
    _reason: QTextEdit
    _buttons: QDialogButtonBox

    def __init__(self,
                 parent: QWidget,
                 source: AbstractEventSource,
                 void: bool):
        super().__init__(parent)
        self._source = source
        self._void = void

        self.setWindowTitle('Confirmation')

        layout = QVBoxLayout(self)

        label = QLabel('Are you sure you want to void current pomodoro?', self)
        layout.addWidget(label)

        self._reason = QTextEdit(self)
        self._reason.setPlaceholderText('Reason (optional)')
        layout.addWidget(self._reason)

        self._warning = QLabel('Pomodoro finished before you saved!', self)
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

    def hideEvent(self, event: QHideEvent) -> None:
        self._source.unsubscribe(self._on_pomodoro_complete)
        super(InterruptionDialog, self).hideEvent(event)

    def _on_pomodoro_complete(self, **_) -> None:
        self._warning.setVisible(True)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _on_action(self, role: QDialogButtonBox.ButtonRole):
        if role == QDialogButtonBox.ButtonRole.AcceptRole:
            print('OK clicked')

        self.close()

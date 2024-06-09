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

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QToolButton

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.desktop.application import Application, AfterSourceChanged

logger = logging.getLogger(__name__)


class ConnectionWidget(QToolButton):
    _application: Application
    _source: AbstractEventSource

    def __init__(self, parent: QWidget, application: Application):
        super().__init__(parent)
        self._application = application
        self._source = None
        self.setObjectName('connectionState')
        self.setIconSize(QSize(32, 32))
        application.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def _update_connection_state(self, is_connected: bool) -> None:
        username = self._application.get_settings().get_username()
        if is_connected:
            self.setIcon(QIcon.fromTheme('conn-online'))
            self.setToolTip('Connected')
            self.topLevelWidget().setWindowTitle(f'Flowkeeper - {username} - Online')
        else:
            self.setIcon(QIcon.fromTheme('conn-offline'))
            self.setToolTip('Disconnected')
            self.topLevelWidget().setWindowTitle(f'Flowkeeper - {username} - Offline')

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._source = source
        self.clicked.connect(self._source.connect)
        self.setVisible(source.can_connect())
        if source.can_connect():
            logger.debug('ConnectionWidget._on_source_changed: Connectable source')
            heartbeat = self._application.get_heartbeat()
            self._update_connection_state(heartbeat.is_online())
            heartbeat.on(events.WentOnline, lambda event, **kwargs: self._update_connection_state(True))
            heartbeat.on(events.WentOffline, lambda event, **kwargs: self._update_connection_state(False))
        else:
            logger.debug('ConnectionWidget._on_source_changed: Offline source')
            self.setIcon(QIcon.fromTheme('conn-unknown'))
            self.setToolTip('N/A')
            self.topLevelWidget().setWindowTitle('Flowkeeper')

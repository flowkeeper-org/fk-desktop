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
import base64
import logging

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor
from PySide6.QtWidgets import QWidget, QToolButton

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.desktop.application import Application, AfterSourceChanged

logger = logging.getLogger(__name__)


class ConnectionWidget(QToolButton):
    _application: Application
    _source: AbstractEventSource
    _userpic: QPixmap
    _is_connected: bool

    def __init__(self, parent: QWidget, application: Application):
        super().__init__(parent)
        self._application = application
        self._source = None
        self._is_connected = False
        self._userpic = None

        self.setObjectName('connectionState')
        self.setIconSize(QSize(32, 32))

        application.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def _update_connection_state(self, is_connected: bool) -> None:
        self._is_connected = is_connected
        self._userpic = QPixmap()
        self._userpic.loadFromData(base64.b64decode(self._application.get_settings().get_userpic()))
        username = self._application.get_settings().get_username()
        if is_connected:
            self.setToolTip(f'Connected - {username}\nClick to reconnect')
            self.topLevelWidget().setWindowTitle(f'Flowkeeper - {username} - Online')
        else:
            self.setToolTip(f'Disconnected - {username}\nClick to reconnect')
            self.topLevelWidget().setWindowTitle(f'Flowkeeper - {username} - Offline')
        self.repaint()

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self._source = source
        self.clicked.connect(self._source.connect)
        self.setVisible(source.can_connect())
        if source.can_connect():
            logger.debug('ConnectionWidget._on_source_changed: Connectable source')
            self._update_connection_state(source.is_online())
            source.on(events.WentOnline, lambda event, **kwargs: self._update_connection_state(True))
            source.on(events.WentOffline, lambda event, **kwargs: self._update_connection_state(False))
        else:
            # This won't be visible, so we don't care about the icon
            logger.debug('ConnectionWidget._on_source_changed: Offline source')
            self.setToolTip('N/A')
            self.topLevelWidget().setWindowTitle('Flowkeeper')

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QBrush(self._userpic))
        painter.drawEllipse(2, 2, self.width() - 3, self.height() - 3)

        dot_size = 12
        painter.setBrush(QBrush(QColor('#AAFF00' if self._is_connected else '#EE4B2B')))
        painter.drawEllipse(self.width() - dot_size, self.height() - dot_size, dot_size, dot_size)

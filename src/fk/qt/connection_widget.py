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
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.desktop.application import Application, AfterSourceChanged
from fk.qt.heartbeat import Heartbeat


class ConnectionWidget(QLabel):
    _img_unknown: QPixmap
    _img_offline: QPixmap
    _img_online: QPixmap

    def __init__(self, parent: QWidget, heartbeat: Heartbeat, app: Application):
        super().__init__(parent)
        self.setObjectName('connectionState')
        self.setFixedSize(QSize(32, 32))

        self._img_online = QPixmap(':/icons/conn-online.svg')
        self._img_offline = QPixmap(':/icons/conn-offline.svg')
        self._img_unknown = QPixmap(':/icons/conn-unknown.svg')

        if heartbeat is not None:
            heartbeat.on(events.WentOnline, lambda event, **kwargs: self._update_connection_state(True))
            heartbeat.on(events.WentOffline, lambda event, **kwargs: self._update_connection_state(False))

        app.on(AfterSourceChanged, lambda event, source: self._update_source(source))
        self._update_source(app.get_source())

    def _update_connection_state(self, is_connected: bool) -> None:
        if is_connected:
            self.setPixmap(self._img_online)
            self.setToolTip('Connected')
            self.topLevelWidget().setWindowTitle('Flowkeeper - Online')
        else:
            self.setPixmap(self._img_offline)
            self.setToolTip('Disconnected')
            self.topLevelWidget().setWindowTitle('Flowkeeper - OFFLINE')

    def _update_source(self, source: AbstractEventSource):
        self.setPixmap(self._img_unknown)
        self.setVisible(source and source.can_connect())
        self.setToolTip('Connecting...')
        self.topLevelWidget().setWindowTitle('Flowkeeper - Connecting...' if source.can_connect() else 'Flowkeeper')

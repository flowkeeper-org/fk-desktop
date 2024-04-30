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


class ConnectionWidget(QLabel):
    _application: Application
    _img_unknown: QPixmap
    _img_offline: QPixmap
    _img_online: QPixmap

    def __init__(self, parent: QWidget, application: Application):
        super().__init__(parent)
        self._application = application
        self.setObjectName('connectionState')
        self.setFixedSize(QSize(32, 32))

        theme = application.get_settings().get('Application.theme')
        self._img_online = QPixmap(f':/icons/{theme}/24x24/conn-online.svg')
        self._img_offline = QPixmap(f':/icons/{theme}/24x24/conn-offline.svg')
        self._img_unknown = QPixmap(f':/icons/{theme}/24x24/conn-unknown.svg')

        application.get_source_holder().on(AfterSourceChanged, self._on_source_changed)

    def _update_connection_state(self, is_connected: bool) -> None:
        if is_connected:
            self.setPixmap(self._img_online)
            self.setToolTip('Connected')
            self.topLevelWidget().setWindowTitle('Flowkeeper - Online')
        else:
            self.setPixmap(self._img_offline)
            self.setToolTip('Disconnected')
            self.topLevelWidget().setWindowTitle('Flowkeeper - OFFLINE')

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.setVisible(source.can_connect())
        if source.can_connect():
            print('ConnectionWidget._on_source_changed: Connectable source')
            heartbeat = self._application.get_heartbeat()
            self._update_connection_state(heartbeat.is_online())
            heartbeat.on(events.WentOnline, lambda event, **kwargs: self._update_connection_state(True))
            heartbeat.on(events.WentOffline, lambda event, **kwargs: self._update_connection_state(False))
        else:
            print('ConnectionWidget._on_source_changed: Offline source')
            self.setPixmap(self._img_unknown)
            self.setToolTip('N/A')
            self.topLevelWidget().setWindowTitle('Flowkeeper')

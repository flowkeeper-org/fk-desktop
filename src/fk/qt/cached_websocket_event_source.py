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
from __future__ import annotations

import atexit
from typing import TypeVar, Generic

from PySide6.QtWidgets import QApplication

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer import AbstractTimer
from fk.core.caching_mixin import CachingMixin
from fk.qt.qt_timer import QtTimer
from fk.qt.websocket_event_source import WebsocketEventSource

TRoot = TypeVar('TRoot')


class CachedWebsocketEventSource(CachingMixin, WebsocketEventSource, Generic[TRoot]):

    _save_timer: AbstractTimer

    def __init__(self,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 application: QApplication,
                 root: TRoot):
        super().__init__(settings=settings,
                         cryptograph=cryptograph,
                         application=application,
                         root=root)
        self._save_timer = QtTimer('WebsocketEventSource_save_cache')
        self._save_timer.schedule(10000,
                                  lambda _1, _2: self.save_cache(),
                                  None,
                                  False)
        atexit.register(self.save_cache)

    def disconnect(self):
        # TODO: Make sure this timer is stopped when we change the source
        self._save_timer.cancel()
        atexit.unregister(self.save_cache)
        super(CachedWebsocketEventSource, self).disconnect()

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

from typing import TypeVar, Generic

from PySide6.QtWidgets import QApplication

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_settings import AbstractSettings
from fk.core.caching_mixin import CachingMixin
from fk.qt.websocket_event_source import WebsocketEventSource

TRoot = TypeVar('TRoot')


class CachedWebsocketEventSource(CachingMixin, WebsocketEventSource, Generic[TRoot]):
    def __init__(self,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 application: QApplication,
                 root: TRoot):
        super().__init__(settings=settings,
                         cryptograph=cryptograph,
                         application=application,
                         root=root)

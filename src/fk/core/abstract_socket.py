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

import logging
from abc import ABC, abstractmethod

from fk.core import events
from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_settings import AbstractSettings

logger = logging.getLogger(__name__)


class AbstractSocket(AbstractEventEmitter, ABC):

    _settings: AbstractSettings

    def __init__(self, settings: AbstractSettings):
        AbstractEventEmitter.__init__(self, [
            events.SocketConnected,
            events.SocketDisconnected,
            events.SocketError,
            events.SocketMessageReceived,
        ], settings.invoke_callback)
        self._settings = settings

    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def send(self, msg: str) -> None:
        pass


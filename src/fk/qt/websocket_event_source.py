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

import datetime
from typing import Self

from PySide6 import QtWebSockets, QtCore

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.abstract_timer import AbstractTimer
from fk.core.strategy_factory import strategy_from_string
from fk.core.user import User
from fk.desktop.desktop_strategies import AuthenticateStrategy, ReplayStrategy
from fk.qt.qt_timer import QtTimer


class WebsocketEventSource(AbstractEventSource):
    _users: dict[str, User]
    _ws: QtWebSockets.QWebSocket
    _mute_requested: bool
    _connection_attempt: int
    _reconnect_timer: AbstractTimer

    def __init__(self, settings: AbstractSettings):
        super().__init__(settings)
        self._users = dict()
        self._users[settings.get_admin()] = User(
            settings.get_admin(),
            'System',
            datetime.datetime.now(),
            True
        )
        self._mute_requested = True
        self._connection_attempt = 0
        self._reconnect_timer = QtTimer()
        self._ws = QtWebSockets.QWebSocket()
        self._ws.connected.connect(lambda: self.replay())
        self._ws.disconnected.connect(lambda: self._connection_lost())
        self._ws.textMessageReceived.connect(lambda msg: self._on_message(msg))

        # Log errors
        self._ws.sslErrors.connect(lambda e: print(f'SslErrors: {e}'))
        self._ws.errorOccurred.connect(lambda e: print(f'ErrorOccurred: {e}'))
        self._ws.handshakeInterruptedOnError.connect(lambda e: print(f'HandshakeInterruptedOnError: {e}'))
        self._ws.peerVerifyError.connect(lambda e: print(f'PeerVerifyError: {e}'))

    def _connection_lost(self):
        next_reconnect = min(max(500, int(pow(1.5, self._connection_attempt))), 30000)
        print(f'WS Client disconnected. Will reconnect in {next_reconnect}ms')
        self._reconnect_timer.schedule(next_reconnect, self._connect, None, True)

    def _connect(self, params: dict | None = None) -> None:
        self._connection_attempt += 1
        url = self.get_config_parameter('WebsocketEventSource.url')
        print(f'Connecting to {url}, attempt {self._connection_attempt}')
        self._ws.open(QtCore.QUrl(url))

    def start(self, mute_events=True) -> None:
        self._last_seq = 0
        self._mute_requested = mute_events
        self._connect()

    def _on_message(self, message: str) -> None:
        lines = message.split('\n')
        print(f'Received: {len(lines)}')
        for line in lines:
            if line == 'ReplayCompleted()':
                if self._mute_requested:
                    self.unmute()
                self._emit(events.SourceMessagesProcessed, dict())
                break
            s = strategy_from_string(line, self._emit, self.get_data(), self._settings)
            if type(s) is str:
                continue
            if s.get_sequence() is not None and s.get_sequence() > self._last_seq:
                if s.get_sequence() != self._last_seq + 1:
                    raise Exception("Strategies must go in sequence")
                self._last_seq = s.get_sequence()
                # print(f" - {s}")
                self._execute_prepared_strategy(s)
        self.auto_seal()

    def replay(self) -> None:
        self._connection_attempt = 0    # This will allow us to reconnect quickly
        print('Connected. Authenticating')
        username = self.get_config_parameter('Source.username')
        token = self.get_config_parameter('WebsocketEventSource.password')
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        auth = AuthenticateStrategy(1,
                                    now,
                                    self._settings.get_admin(),
                                    [username, token],
                                    None,
                                    self._users,
                                    None)
        self._ws.sendTextMessage(str(auth))

        print(f'Requesting replay starting from #{self._last_seq}')
        replay = ReplayStrategy(2,
                                now,
                                self._settings.get_admin(),
                                [str(self._last_seq)],
                                None,
                                self._users,
                                None)
        self._ws.sendTextMessage(str(replay))

        self._emit(events.SourceMessagesRequested, dict())
        if self._mute_requested:
            self.mute()

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        for s in strategies:
            self._ws.sendTextMessage(str(s))

    def get_name(self) -> str:
        return "Websocket"

    def get_data(self) -> dict[str, User]:
        return self._users

    def clone(self) -> Self:
        return WebsocketEventSource(self._settings)

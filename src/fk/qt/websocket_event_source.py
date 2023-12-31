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
import enum
from typing import Self, TypeVar

from PySide6 import QtWebSockets, QtCore
from PySide6.QtNetwork import QAbstractSocket

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.abstract_timer import AbstractTimer
from fk.core.strategy_factory import strategy_from_string
from fk.desktop.desktop_strategies import AuthenticateStrategy, ReplayStrategy, ErrorStrategy
from fk.qt.qt_timer import QtTimer

TRoot = TypeVar('TRoot')


class WebsocketEventSource(AbstractEventSource):
    _data: TRoot
    _ws: QtWebSockets.QWebSocket
    _mute_requested: bool
    _connection_attempt: int
    _reconnect_timer: AbstractTimer
    _received_error: bool
    _ignore_invalid_sequences: bool
    _ignore_errors: bool

    def __init__(self,
                 settings: AbstractSettings,
                 root: TRoot):
        super().__init__(settings)
        self._data = root
        self._mute_requested = True
        self._connection_attempt = 0
        self._received_error = False
        self._reconnect_timer = QtTimer()
        self._ws = QtWebSockets.QWebSocket()
        self._ws.connected.connect(lambda: self.replay())
        self._ws.disconnected.connect(lambda: self._connection_lost())
        self._ws.textMessageReceived.connect(lambda msg: self._on_message(msg))

        self._ignore_invalid_sequences = settings.get('WebsocketEventSource.ignore_invalid_sequence') == 'True'
        self._ignore_errors = settings.get('WebsocketEventSource.ignore_errors') == 'True'

        # Log errors
        self._ws.sslErrors.connect(lambda e: self._on_error('SSL error', e))
        self._ws.errorOccurred.connect(lambda e: self._on_error('error occurred', e))
        self._ws.handshakeInterruptedOnError.connect(lambda e: self._on_error('handshake interrupted on error', e))
        self._ws.peerVerifyError.connect(lambda e: self._on_error('peer verify error', e))

    def _on_error(self, s: str, e: enum) -> None:
        if type(e) != QAbstractSocket.SocketError:
            raise Exception(f'WebSocket {s}: {e}')

    def _connection_lost(self) -> None:
        next_reconnect = min(max(500, int(pow(1.5, self._connection_attempt))), 30000)
        if self._received_error:
            print(f'WebSocket disconnected due to an error reported by the server. Will not try to reconnect.')
        else:
            print(f'WebSocket disconnected for unknown reason. Will attempt to reconnect in {next_reconnect}ms')
            self._reconnect_timer.schedule(next_reconnect, self._connect, None, True)

    def _connect(self, params: dict | None = None) -> None:
        self._connection_attempt += 1
        source_type = self.get_config_parameter('Source.type')
        if source_type == 'websocket':
            url = self.get_config_parameter('WebsocketEventSource.url')
        elif source_type == 'flowkeeper.org':
            url = 'wss://app.flowkeeper.org'
        elif source_type == 'flowkeeper.pro':
            url = 'wss://app.flowkeeper.pro'
        else:
            raise Exception(f"Unexpected source type for WebSocket event source: {source_type}")
        print(f'Connecting to {url}, attempt {self._connection_attempt}')
        self._ws.open(QtCore.QUrl(url))

    def start(self, mute_events=True) -> None:
        self._last_seq = 0
        self._mute_requested = mute_events
        self._connect()

    def _on_message(self, message: str) -> None:
        lines = message.split('\n')
        print(f'Received {len(lines)} messages')
        for line in lines:
            try:
                if line == 'ReplayCompleted()':
                    if self._mute_requested:
                        self.unmute()
                    self._emit(events.SourceMessagesProcessed, dict())
                    break
                s = strategy_from_string(line, self._emit, self.get_data(), self._settings)
                if type(s) is str:
                    continue
                if type(s) is ErrorStrategy:
                    self._received_error = True
                    s.execute()  # This will throw an exception
                if s.get_sequence() is not None and s.get_sequence() > self._last_seq:
                    if not self._ignore_invalid_sequences and s.get_sequence() != self._last_seq + 1:
                        self._sequence_error(self._last_seq, s.get_sequence())
                    self._last_seq = s.get_sequence()
                    # print(f" - {s}")
                    self._execute_prepared_strategy(s)
            except Exception as ex:
                if self._ignore_errors:
                    print(f'Error processing {line}: {ex}')
                else:
                    raise ex
        self.auto_seal()

    def replay(self) -> None:
        self._connection_attempt = 0    # This will allow us to reconnect quickly
        self._received_error = False
        print('Connected. Authenticating')
        username = self.get_config_parameter('WebsocketEventSource.username')
        token = self.get_config_parameter('WebsocketEventSource.password')
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        auth = AuthenticateStrategy(1,
                                    now,
                                    self._data.get_admin_user(),
                                    [username, token],
                                    self._emit,
                                    self._data,
                                    self._settings)
        self._ws.sendTextMessage(str(auth))

        print(f'Requesting replay starting from #{self._last_seq}')
        replay = ReplayStrategy(2,
                                now,
                                self._data.get_admin_user(),
                                [str(self._last_seq)],
                                self._emit,
                                self._data,
                                self._settings)
        self._ws.sendTextMessage(str(replay))

        self._emit(events.SourceMessagesRequested, dict())
        if self._mute_requested:
            self.mute()

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        for s in strategies:
            self._ws.sendTextMessage(str(s))

    def get_name(self) -> str:
        return "Websocket"

    def get_data(self) -> TRoot:
        return self._data

    def clone(self, new_root: TRoot) -> Self:
        return WebsocketEventSource(self._settings, new_root)

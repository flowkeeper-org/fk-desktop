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

import json
import logging
import shlex
from subprocess import Popen

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.abstract_settings import AbstractSettings
from fk.core.events import AfterSettingsChanged, ALL_EVENTS, set_emitter_added_callback
from fk.qt.sandbox import get_sandbox_type

logger = logging.getLogger(__name__)


class IntegrationExecutor:
    _settings: AbstractSettings
    _subscribed: dict[str, str]

    def __init__(self, settings: AbstractSettings):
        super().__init__()
        self._settings = settings
        self._subscribed = dict()
        settings.on(AfterSettingsChanged, self._on_setting_changed)
        set_emitter_added_callback(self._on_emitter_added)
        self._resync_subscriptions_from_settings()

    def _on_emitter_added(self, emitter: object):
        self._resync_subscriptions_from_settings()

    def _on_setting_changed(self, new_values: dict[str, str], **kwargs):
        if 'Integration.callbacks' in new_values:
            self._sync_subscriptions(json.loads(new_values['Integration.callbacks']))

    def _resync_subscriptions_from_settings(self) -> None:
        self._sync_subscriptions(json.loads(self._settings.get('Integration.callbacks')))

    def _sync_subscriptions(self, new_conf: dict[str, str]) -> None:
        for event in new_conf:
            if event in self._subscribed:
                if self._subscribed[event] != new_conf[event]:
                    self._subscribed[event] = new_conf[event]
            else:
                if event in ALL_EVENTS:     # The corresponding emitter might not have initialized yet
                    emitter: AbstractEventEmitter = ALL_EVENTS[event].emitter
                    emitter.on(ALL_EVENTS[event].event,
                               lambda **kwargs: self.on_event(event, **kwargs),
                               True)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Subscribed to {event}')
                    self._subscribed[event] = new_conf[event]
        to_delete: set[str] = set()
        for event in self._subscribed:
            if event not in new_conf:
                emitter: AbstractEventEmitter = ALL_EVENTS[event].emitter
                emitter.unsubscribe_one(self.on_event, ALL_EVENTS[event].event)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Unsubscribed from {event}')
                to_delete.add(event)
        for event in to_delete:
            del self._subscribed[event]

    def on_event(self, full_event, **kwargs):
        if full_event in self._subscribed:
            command = self._subscribed[full_event]
            formatted = eval(f"f'{command}'", kwargs)   # Kwargs parameter here is important -- it limits eval() scope
            # This is a safer, but less flexible alternative:
            # formatted = command.format(**kwargs)
            args = shlex.split(formatted)
            if get_sandbox_type() == 'Flatpak' and self._settings.get('Integration.flatpak_spawn') == 'True':
                # Use flatpak-spawn to execute commands outside the sandbox
                args.insert(0, 'flatpak-spawn')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Received event {full_event}. Executing: {args}')
            Popen(args)

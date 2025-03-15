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
import abc
from typing import Callable
from unittest import TestCase

from fk.core.abstract_event_emitter import AbstractEventEmitter


class AbstractTestCase(TestCase, abc.ABC):
    def assert_events(self,
                      emitter: AbstractEventEmitter,
                      action: Callable,
                      expected_events: list[str],
                      expected_params: dict[str, dict[str, any]] = None):
        fired = list()

        def on_event(event, **kwargs):
            fired.append(event)
            if expected_params is not None:
                params = expected_params.get(event)
                if params is not None:
                    for name in params:
                        self.assertIn(name, kwargs)
                        self.assertEqual(kwargs[name], params[name])

        emitter.on('*', on_event)
        action()
        self.assertEqual(len(fired), len(expected_events))
        for i in range(len(expected_events)):
            self.assertEqual(fired[i], expected_events[i])

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
import logging
from typing import Callable

from fk.core.abstract_event_emitter import AbstractEventEmitter
from fk.core.mock_settings import invoke_direct
from fk.tests.abstract_test_case import AbstractTestCase

BeforeAction = 'BeforeAction'
AfterAction = 'AfterAction'


class TestEmitter(AbstractEventEmitter):
    value: str | None

    def __init__(self,
                 invoker: Callable = invoke_direct):
        AbstractEventEmitter.__init__(self, [
            BeforeAction,
            AfterAction,
        ], invoker)
        self.value = None

    def action(self, value: str, carry: str = None):
        self._emit(BeforeAction, {'value': value}, carry)
        self.value = value
        self._emit(AfterAction, {'value': value}, carry)

    def wrong_emit(self):
        self._emit('WrongEvent', {'value': 'one'}, None)


class TestEvents(AbstractTestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)

    def test_events_basic(self):
        emitter = TestEmitter()
        self.assert_events(emitter,
                           lambda: emitter.action('foo'),
                           ['BeforeAction', 'AfterAction'],
                           {
                               'BeforeAction': {'value': 'foo'},
                               'AfterAction': {'value': 'foo'}
                           })

    # - Callback invoker is used every time
    def test_callback_invoker(self):
        fired = list()

        def invoke(fn, **kwargs):
            fired.append(kwargs['event'])
            fn(**kwargs)

        def on_event(event, **kwargs):
            pass

        emitter = TestEmitter(invoke)
        emitter.on('*', on_event)
        emitter.action('foo')
        self.assertEqual(len(fired), 2)
        self.assertEqual(fired[0], 'BeforeAction')
        self.assertEqual(fired[1], 'AfterAction')

    def test_cancel_one(self):
        fired = False
        def on_event(event, **kwargs):
            self.assertEqual(event, 'AfterAction')
            nonlocal fired
            fired = True
        emitter = TestEmitter()
        emitter.on('*', on_event, True)
        emitter.cancel('BeforeAction')
        emitter.action('foo')
        self.assertTrue(fired)

    def test_unsubscribe(self):
        def on_event(event, **kwargs):
            self.assertTrue(False)
        emitter = TestEmitter()
        emitter.on('BeforeAction', on_event, True)
        emitter.on('AfterAction', on_event, True)
        emitter.unsubscribe(on_event)
        emitter.action('foo')

    def test_unsubscribe_one(self):
        fired = False
        def on_event(event, **kwargs):
            self.assertEqual(event, 'BeforeAction')
            nonlocal fired
            fired = True
        emitter = TestEmitter()
        emitter.on('BeforeAction', on_event, True)
        emitter.on('AfterAction', on_event, True)
        emitter.unsubscribe_one(on_event, 'AfterAction')
        emitter.action('foo')
        self.assertTrue(fired)

    def test_firing_order(self):
        fired1 = False
        fired2 = False
        def on_event1(event, **kwargs):
            nonlocal fired1
            nonlocal fired2
            self.assertFalse(fired1)
            self.assertFalse(fired2)
            fired1 = True
        def on_event2(event, **kwargs):
            nonlocal fired1
            nonlocal fired2
            self.assertTrue(fired1)
            self.assertFalse(fired2)
            fired2 = True

        emitter = TestEmitter()

        emitter.on('BeforeAction', on_event1, False)
        emitter.on('BeforeAction', on_event2, True)
        emitter.action('foo')
        self.assertTrue(fired1 and fired2)
        fired1 = False
        fired2 = False
        emitter.cancel('BeforeAction')

        emitter.on('BeforeAction', on_event1, False)
        emitter.on('BeforeAction', on_event2, False)
        emitter.action('foo')
        self.assertTrue(fired1 and fired2)
        fired1 = False
        fired2 = False
        emitter.cancel('BeforeAction')

        emitter.on('BeforeAction', on_event2, True)
        emitter.on('BeforeAction', on_event1, False)
        emitter.action('foo')
        self.assertTrue(fired1 and fired2)
        fired1 = False
        fired2 = False
        emitter.cancel('BeforeAction')

    # Tests:
    # + Two priorities ("last" callbacks)
    # + Subscribe with wildcards
    # + Subscribe to a single event
    # - Carry parameter
    # - No duplicate subscriptions
    # + Canceling subscriptions
    # + Unsubscribing from emitter
    # - Emitting events with parameters
    # - Error when trying to emit something new
    # - Mute / unmute events
    # - "Event" parameter

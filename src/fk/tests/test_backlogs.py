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
import logging
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.backlog_strategies import RenameBacklogStrategy, DeleteBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro_strategies import AddPomodoroStrategy
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy
from fk.tests.test_utils import (predefined_datetime, noop_emit, test_settings,
                                 TEST_USERNAMES, predefined_uid, check_timestamp, test_data)


def _create_sample_backlog(existing: Tenant | None = None) -> Tenant:
    data = test_data() if existing is None else existing
    s = CreateBacklogStrategy(
        1,
        predefined_datetime(0),
        TEST_USERNAMES[0],
        [predefined_uid(0), 'Basic Test'],
        test_settings(0))
    s.execute(noop_emit, data)
    return data


class TestBacklogs(TestCase):
    settings: AbstractSettings
    cryptograph: AbstractCryptograph
    source: EphemeralEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self.settings = MockSettings()
        self.cryptograph = NoCryptograph(self.settings)
        self.source = EphemeralEventSource[Tenant](self.settings, self.cryptograph, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        self.source.dump()

    def test_initialize(self):
        self.assertIn('user@local.host', self.data)
        user = self.data['user@local.host']
        self.assertEqual(len(user), 0)

    def _assert_backlog(self, backlog1: Backlog, user: User):
        self.assertEqual(backlog1.get_name(), 'First backlog')
        self.assertEqual(backlog1.get_uid(), '123-456-789-1')
        self.assertEqual(backlog1.get_parent(), user)
        self.assertEqual(backlog1.get_owner(), user)
        self.assertTrue(backlog1.is_today())
        self.assertEqual(backlog1.get_running_workitem(), (None, None))
        self.assertEqual(len(backlog1.values()), 0)

    def test_create_backlogs(self):
        user = self.data['user@local.host']
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.assertIn('123-456-789-1', user)
        self.assertIn('123-456-789-2', user)
        backlog1: Backlog = user['123-456-789-1']
        self._assert_backlog(backlog1, user)
        backlog2 = user['123-456-789-2']
        self.assertEqual(backlog2.get_name(), 'Second backlog')

    def test_execute_prepared(self):
        user = self.data['user@local.host']
        s = CreateBacklogStrategy(2,
                                  datetime.datetime.now(datetime.timezone.utc),
                                  user.get_identity(),
                                  ['123-456-789-1', 'First backlog'],
                                  self.settings)
        self.source.execute_prepared_strategy(s)
        self.assertIn('123-456-789-1', user)
        backlog1: Backlog = user['123-456-789-1']
        self._assert_backlog(backlog1, user)

    def test_create_duplicate_backlog_failure(self):
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog 1'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog 2']))

    def test_rename_nonexistent_backlog_failure(self):
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(RenameBacklogStrategy, ['123-456-789-3', 'Renamed backlog']))

    def test_rename_backlog(self):
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(RenameBacklogStrategy, ['123-456-789-1', 'Renamed backlog'])
        user = self.data['user@local.host']
        self.assertEqual(user['123-456-789-1'].get_name(), 'Renamed backlog')

    def test_delete_nonexistent_backlog_failure(self):
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(DeleteBacklogStrategy, ['123-456-789-3']))

    def test_delete_backlog(self):
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.source.execute(DeleteBacklogStrategy, ['123-456-789-1'])
        user = self.data['user@local.host']
        self.assertNotIn('123-456-789-1', user)
        self.assertIn('123-456-789-2', user)

    def test_today(self):
        user = self.data['user@local.host']
        s = CreateBacklogStrategy(2,
                                  datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24),
                                  user.get_identity(),
                                  ['123-456-789-1', 'First backlog'],
                                  self.settings)
        self.source.execute_prepared_strategy(s)
        backlog = user['123-456-789-1']
        self.assertFalse(backlog.is_today())

    def test_events_create_backlog(self):
        # Subscribe to all events and check that only required ones fire
        # Ephemeral event source is synchronous, so it's alright that we don't add any delays here
        state = 0
        fired = list()
        def on_event(event, **kwargs):
            self.assertNotIn(state, [0, 2])
            self.assertIn(event, ['BeforeMessageProcessed', 'BeforeBacklogCreate', 'AfterBacklogCreate', 'AfterMessageProcessed'])
            fired.append(event)
            if event == 'BeforeMessageProcessed' or event == 'AfterMessageProcessed':
                self.assertIn('strategy', kwargs)
                self.assertIn('auto', kwargs)
                self.assertIn('persist', kwargs)
                self.assertTrue(type(kwargs['strategy']) is CreateBacklogStrategy)
            elif event == 'BeforeBacklogCreate':
                self.assertIn('backlog_owner', kwargs)
                self.assertIn('backlog_uid', kwargs)
                self.assertIn('backlog_name', kwargs)
                self.assertTrue(type(kwargs['backlog_owner']) is User)
                self.assertEqual(kwargs['backlog_uid'], '123-456-789-1')
                self.assertEqual(kwargs['backlog_name'], 'First backlog')
            elif event == 'AfterBacklogCreate':
                self.assertIn('backlog', kwargs)
                self.assertTrue(type(kwargs['backlog']) is Backlog)
        self.source.on('*', on_event)
        state = 1
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        state = 2
        self.assertEqual(len(fired), 4)

    def test_events_delete_backlog(self):
        # Here we shall also test the recursive deletion
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeBacklogDelete' or event == 'AfterBacklogDelete':
                self.assertIn('backlog', kwargs)
                self.assertTrue(type(kwargs['backlog']) is Backlog)
                self.assertEqual(kwargs['backlog'].get_name(), 'First backlog')
            elif event == 'BeforeWorkitemDelete' or event == 'AfterWorkitemDelete':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)
                self.assertIn(kwargs['workitem'].get_name(), ['First item', 'Second item'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateWorkitemStrategy, ['w1', '123-456-789-1', 'First item'])
        self.source.execute(AddPomodoroStrategy, ['w1', '2'])
        self.source.execute(CreateWorkitemStrategy, ['w2', '123-456-789-1', 'Second item'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.source.execute(CreateWorkitemStrategy, ['w3', '123-456-789-2', 'Third item'])
        self.source.on('*', on_event)  # We only care about delete here
        self.source.execute(DeleteBacklogStrategy, ['123-456-789-1'])
        self.assertEqual(len(fired), 12)  # Note that although we had a cascade delete, only one strategy got executed
        # The events must arrive in the right order, too
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeBacklogDelete')
        self.assertEqual(fired[2], 'BeforeMessageProcessed')  # auto=True
        self.assertEqual(fired[3], 'BeforeWorkitemDelete')
        self.assertEqual(fired[4], 'AfterWorkitemDelete')
        self.assertEqual(fired[5], 'AfterMessageProcessed')  # auto=True
        self.assertEqual(fired[6], 'BeforeMessageProcessed')  # auto=True
        self.assertEqual(fired[7], 'BeforeWorkitemDelete')
        self.assertEqual(fired[8], 'AfterWorkitemDelete')
        self.assertEqual(fired[9], 'AfterMessageProcessed')  # auto=True
        self.assertEqual(fired[10], 'AfterBacklogDelete')
        self.assertEqual(fired[11], 'AfterMessageProcessed')        
        # Automatic voiding of pomodoros will be tested when we cover the lifecycles

    def test_events_rename_backlog(self):
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeBacklogRename' or event == 'AfterBacklogRename':
                self.assertIn('backlog', kwargs)
                self.assertIn('old_name', kwargs)
                self.assertIn('new_name', kwargs)
                self.assertEqual(kwargs['old_name'], 'Before')
                self.assertEqual(kwargs['new_name'], 'After')
                self.assertTrue(type(kwargs['backlog']) is Backlog)                    
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'Before'])
        self.source.on('*', on_event)
        self.source.execute(RenameBacklogStrategy, ['123-456-789-1', 'After'])
        self.assertEqual(len(fired), 4)
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeBacklogRename')
        self.assertEqual(fired[2], 'AfterBacklogRename')
        self.assertEqual(fired[3], 'AfterMessageProcessed')

    def test_create_backlog_strategy_basic(self):
        data = _create_sample_backlog()
        self.assertEqual(4, len(data))   # It also includes admin user
        user = data[TEST_USERNAMES[0]]
        self.assertEqual(1, len(user))
        self.assertIn(predefined_uid(0), user)
        backlog = user[predefined_uid(0)]
        self.assertEqual('Basic Test', backlog.get_name())
        self.assertEqual(predefined_uid(0), backlog.get_uid())
        self.assertEqual(user, backlog.get_parent())
        self.assertEqual(user, backlog.get_owner())
        self.assertTrue(check_timestamp(backlog.get_create_date(), 0))
        self.assertIsNone(backlog.get_running_workitem()[0])
        self.assertIsNone(backlog.get_running_workitem()[1])
        self.assertTrue(check_timestamp(backlog.get_last_modified_date(), 0))

    def test_create_backlog_strategy_already_exists(self):
        data = _create_sample_backlog()
        with self.assertRaises(Exception):
            _create_sample_backlog(data)

    def test_create_backlog_strategy_same_name(self):
        data = _create_sample_backlog()
        s = CreateBacklogStrategy(
            2,
            predefined_datetime(1),
            TEST_USERNAMES[0],
            [predefined_uid(1), 'Basic Test'],
            test_settings(0))
        s.execute(noop_emit, data)
        user = data[TEST_USERNAMES[0]]
        self.assertEqual(user[predefined_uid(0)].get_name(), 'Basic Test')
        self.assertEqual(user[predefined_uid(1)].get_name(), 'Basic Test')
        self.assertNotEqual(user[predefined_uid(0)], user[predefined_uid(1)])

    def test_create_backlog_independent_users_same_uid(self):
        data = _create_sample_backlog()
        s = CreateBacklogStrategy(
            2,
            predefined_datetime(1),
            TEST_USERNAMES[1],
            [predefined_uid(0), 'Second Backlog'],
            test_settings(1))
        s.execute(noop_emit, data)
        user1 = data[TEST_USERNAMES[0]]
        user2 = data[TEST_USERNAMES[1]]
        user3 = data[TEST_USERNAMES[2]]
        self.assertEqual(len(user1), 1)
        self.assertEqual(user1[predefined_uid(0)].get_name(), 'Basic Test')
        self.assertEqual(len(user2), 1)
        self.assertEqual(user2[predefined_uid(0)].get_name(), 'Second Backlog')
        self.assertEqual(len(user3), 0)

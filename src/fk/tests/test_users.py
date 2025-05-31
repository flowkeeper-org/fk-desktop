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
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.mock_settings import MockSettings
from fk.core.tenant import ADMIN_USER
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.user_strategies import CreateUserStrategy, RenameUserStrategy, DeleteUserStrategy
from fk.tests.test_utils import (epyc)


class TestUsers(TestCase):
    settings: AbstractSettings
    cryptograph: AbstractCryptograph
    source: EphemeralEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self.settings = MockSettings()
        self.cryptograph = FernetCryptograph(self.settings)
        self.source = EphemeralEventSource[Tenant](self.settings, self.cryptograph, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        self.source.dump()

    def _assert_user(self, user: User):
        self.assertEqual(user.get_name(), 'Alice Cooper')
        self.assertEqual(user.get_uid(), 'u1')
        self.assertEqual(user.get_parent(), self.data)
        self.assertEqual(user.get_owner(), None)
        self.assertEqual(len(user.values()), 0)
        self.assertEqual(len(user.get_tags()), 0)

    def _create_standard_user(self):
        self.source.execute_prepared_strategy(
            CreateUserStrategy(2, epyc(), ADMIN_USER, ['u1', 'Alice Cooper'], self.settings, None))

    def test_create_user(self):
        self._create_standard_user()
        self.assertIn('u1', self.data)
        self._assert_user(self.data['u1'])

    def test_create_user_unauthorized_failure(self):
        self.assertRaises(Exception,
                          lambda: self.source.execute(CreateUserStrategy, ['u1', 'Alice Cooper']))

    def test_create_duplicate_user_failure(self):
        self._create_standard_user()
        self.assertRaises(Exception, self._create_standard_user)

    def test_rename_nonexistent_user_failure(self):
        self._create_standard_user()
        self.assertRaises(Exception,
                          lambda: self.source.execute_prepared_strategy(
                              RenameUserStrategy(3, epyc(), ADMIN_USER, ['u2', 'Bob'], self.settings, None)))

    def test_rename_user(self):
        self._create_standard_user()
        self.source.execute_prepared_strategy(
            RenameUserStrategy(3, epyc(), ADMIN_USER, ['u1', 'Bob'], self.settings, None))
        self.assertEqual(self.data['u1'].get_name(), 'Bob')

    def test_delete_nonexistent_user_failure(self):
        self._create_standard_user()
        self.assertRaises(Exception,
                          lambda: self.source.execute_prepared_strategy(
                              DeleteUserStrategy(3, epyc(), ADMIN_USER, ['u2'], self.settings, None)))

    def test_delete_user(self):
        self._create_standard_user()
        self.source.execute_prepared_strategy(
            DeleteUserStrategy(3, epyc(), ADMIN_USER, ['u1'], self.settings, None))
        self.assertNotIn('u1', self.data)

    def test_events_create_user(self):
        fired = list()
        def on_event(event, **kwargs):
            self.assertIn(event, ['BeforeMessageProcessed', 'BeforeUserCreate', 'AfterUserCreate', 'AfterMessageProcessed'])
            fired.append(event)
            if event == 'BeforeMessageProcessed' or event == 'AfterMessageProcessed':
                self.assertIn('strategy', kwargs)
                self.assertIn('auto', kwargs)
                self.assertIn('persist', kwargs)
                self.assertTrue(type(kwargs['strategy']) is CreateUserStrategy)
            elif event == 'BeforeUserCreate':
                self.assertIn('user_identity', kwargs)
                self.assertIn('user_name', kwargs)
                self.assertEqual(kwargs['user_identity'], 'u1')
                self.assertEqual(kwargs['user_name'], 'Alice Cooper')
            elif event == 'AfterUserCreate':
                self.assertIn('user', kwargs)
                self.assertTrue(type(kwargs['user']) is User)
        self.source.on('*', on_event)
        self._create_standard_user()
        self.assertEqual(len(fired), 4)

    def test_events_delete_user(self):
        # Here we shall also test the recursive deletion
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeUserDelete' or event == 'AfterUserDelete':
                self.assertIn('user', kwargs)
                self.assertTrue(type(kwargs['user']) is User)
                self.assertEqual(kwargs['user'].get_name(), 'Local User')
            elif event == 'BeforeBacklogDelete' or event == 'AfterBacklogDelete':
                self.assertIn('backlog', kwargs)
                self.assertTrue(type(kwargs['backlog']) is Backlog)
                self.assertEqual(kwargs['backlog'].get_name(), 'Backlog')
        self.source.execute(CreateBacklogStrategy, ['b1', 'Backlog'])
        self.source.on('*', on_event)  # We only care about delete here
        self.source.execute_prepared_strategy(
            DeleteUserStrategy(2, epyc(), ADMIN_USER, ['user@local.host'], self.settings, None))
        self.assertEqual(len(fired), 8)
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeUserDelete')
        self.assertEqual(fired[2], 'BeforeMessageProcessed')  # auto=True
        self.assertEqual(fired[3], 'BeforeBacklogDelete')
        self.assertEqual(fired[4], 'AfterBacklogDelete')
        self.assertEqual(fired[5], 'AfterMessageProcessed')  # auto=True
        self.assertEqual(fired[6], 'AfterUserDelete')
        self.assertEqual(fired[7], 'AfterMessageProcessed')

    def test_events_rename_user(self):
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeUserRename' or event == 'AfterUserRename':
                self.assertIn('user', kwargs)
                self.assertIn('old_name', kwargs)
                self.assertIn('new_name', kwargs)
                self.assertEqual(kwargs['old_name'], 'Alice Cooper')
                self.assertEqual(kwargs['new_name'], 'Bob')
                self.assertTrue(type(kwargs['user']) is User)
        self._create_standard_user()
        self.source.on('*', on_event)
        self.source.execute_prepared_strategy(
            RenameUserStrategy(3, epyc(), ADMIN_USER, ['u1', 'Bob'], self.settings, None))
        self.assertEqual(len(fired), 4)
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeUserRename')
        self.assertEqual(fired[2], 'AfterUserRename')
        self.assertEqual(fired[3], 'AfterMessageProcessed')

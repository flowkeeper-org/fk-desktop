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
from unittest import TestCase

from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, RenameBacklogStrategy, DeleteBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User


class TestBacklogs(TestCase):
    settings: AbstractSettings
    source: EphemeralEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        self.settings = MockSettings()
        self.source = EphemeralEventSource(self.settings, Tenant(self.settings))
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
                                  user,
                                  ['123-456-789-1', 'First backlog'],
                                  self.source._emit,
                                  self.data,
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

    def test_delete_backlog_content(self):
        # TODO: Recursive delete
        self.source.execute(CreateBacklogStrategy, ['123-456-789-1', 'First backlog'])
        self.source.execute(CreateBacklogStrategy, ['123-456-789-2', 'Second backlog'])
        self.source.execute(DeleteBacklogStrategy, ['123-456-789-1'])
        user = self.data['user@local.host']
        self.assertNotIn('123-456-789-1', user)
        self.assertIn('123-456-789-2', user)

    def test_today(self):
        user = self.data['user@local.host']
        s = CreateBacklogStrategy(2,
                                  datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=14),
                                  user,
                                  ['123-456-789-1', 'First backlog'],
                                  self.source._emit,
                                  self.data,
                                  self.settings)
        self.source.execute_prepared_strategy(s)
        backlog = user['123-456-789-1']
        self.assertFalse(backlog.is_today())

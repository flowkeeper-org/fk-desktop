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

from unittest import TestCase

from fk.core.tenant import Tenant
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.tests.test_utils import (predefined_datetime, noop_emit, test_settings,
                                 test_users, TEST_USERNAMES, predefined_uid, check_timestamp, test_data)


class TestBacklogStrategies(TestCase):
    @staticmethod
    def _create_sample_backlog(existing: Tenant | None = None) -> Tenant:
        data = test_data() if existing is None else existing
        s = CreateBacklogStrategy(
            1,
            predefined_datetime(0),
            test_users()[TEST_USERNAMES[0]],
            [predefined_uid(0), 'Basic Test'],
            noop_emit,
            data,
            test_settings(0))
        s.execute()
        return data

    def test_create_backlog_strategy_basic(self):
        data = TestBacklogStrategies._create_sample_backlog()
        self.assertEqual(4, len(data.keys()))   # It also includes admin user
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
        data = TestBacklogStrategies._create_sample_backlog()
        with self.assertRaises(Exception):
            TestBacklogStrategies._create_sample_backlog(data)

    def test_create_backlog_strategy_same_name(self):
        data = TestBacklogStrategies._create_sample_backlog()
        s = CreateBacklogStrategy(
            2,
            predefined_datetime(1),
            test_users()[TEST_USERNAMES[0]],
            [predefined_uid(1), 'Basic Test'],
            noop_emit,
            data,
            test_settings(0))
        s.execute()
        user = data[TEST_USERNAMES[0]]
        self.assertEqual(user[predefined_uid(0)].get_name(), 'Basic Test')
        self.assertEqual(user[predefined_uid(1)].get_name(), 'Basic Test')
        self.assertNotEqual(user[predefined_uid(0)], user[predefined_uid(1)])

    def test_create_backlog_independent_users_same_uid(self):
        data = TestBacklogStrategies._create_sample_backlog()
        s = CreateBacklogStrategy(
            2,
            predefined_datetime(1),
            test_users()[TEST_USERNAMES[1]],
            [predefined_uid(0), 'Second Backlog'],
            noop_emit,
            data,
            test_settings(1))
        s.execute()
        user1 = data[TEST_USERNAMES[0]]
        user2 = data[TEST_USERNAMES[1]]
        user3 = data[TEST_USERNAMES[2]]
        self.assertEqual(len(user1), 1)
        self.assertEqual(user1[predefined_uid(0)].get_name(), 'Basic Test')
        self.assertEqual(len(user2), 1)
        self.assertEqual(user2[predefined_uid(0)].get_name(), 'Second Backlog')
        self.assertEqual(len(user3), 0)

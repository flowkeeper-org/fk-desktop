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
from fk.core.category_strategies import CreateCategoryStrategy, DeleteCategoryStrategy, RenameCategoryStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.tenant import Tenant
from fk.core.user import User


class TestCategories(TestCase):
    settings: AbstractSettings
    cryptograph: AbstractCryptograph
    source: EphemeralEventSource
    data: Tenant

    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self.settings = MockSettings()
        self.cryptograph = NoCryptograph(self.settings)
        self.source = EphemeralEventSource[Tenant](self.settings, self.cryptograph, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        self.source.dump()

    def test_create_category(self):
        user: User = self.data.get_current_user()
        self.assertIsNotNone(user.get_root_category())
        self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Category 1'])
        self.assertIsNotNone(user.find_category_by_id('c1'))
        self.source.execute(CreateCategoryStrategy, ['c11', 'c1', 'Category 2'])
        self.assertIsNotNone(user.find_category_by_id('c11'))
        self.assertIsNotNone(user.find_category_by_id('c11', user.find_category_by_id('c1')))

    def test_delete_category(self):
        user: User = self.data.get_current_user()
        self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Category 1'])
        self.assertIsNotNone(user.find_category_by_id('c1'))
        self.source.execute(DeleteCategoryStrategy, ['c1'])
        self.assertIsNone(user.find_category_by_id('c1'))

        self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Category 1'])
        self.source.execute(CreateCategoryStrategy, ['c11', 'c1', 'Category 2'])
        self.source.execute(DeleteCategoryStrategy, ['c1'])
        self.assertIsNone(user.find_category_by_id('c1'))
        self.assertIsNone(user.find_category_by_id('c11'))

    def test_rename_category(self):
        user: User = self.data.get_current_user()
        self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Category 1'])
        self.assertEqual(user.find_category_by_id('c1').get_name(), 'Category 1')
        self.source.execute(RenameCategoryStrategy, ['c1', 'Category 2'])
        self.assertEqual(user.find_category_by_id('c1').get_name(), 'Category 2')

    def test_failures(self):
        self.assertRaises(
            Exception,
            lambda: self.source.execute(CreateCategoryStrategy, ['c1', 'nonexistent', 'Category 1']))

        self.assertRaises(
            Exception,
            lambda: self.source.execute(CreateCategoryStrategy, ['c1', None, 'Category 1']))

        self.assertRaises(
            Exception,
            lambda: self.source.execute(CreateCategoryStrategy, ['c1', '', 'Category 1']))

        self.assertRaises(
            Exception,
            lambda: self.source.execute(CreateCategoryStrategy, ['#root', '#root', 'Category 1']))

        self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Category 1'])
        self.assertRaises(
            Exception,
            lambda: self.source.execute(CreateCategoryStrategy, ['c1', '#root', 'Duplicate']))

        self.assertRaises(
            Exception,
            lambda: self.source.execute(RenameCategoryStrategy, ['c2', 'Category 2']))

        self.assertRaises(
            Exception,
            lambda: self.source.execute(RenameCategoryStrategy, ['#root', 'Root']))


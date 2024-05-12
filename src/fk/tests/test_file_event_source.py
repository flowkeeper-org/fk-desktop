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
import os
from unittest import TestCase

from fk.core.abstract_settings import AbstractSettings
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User

TEMP_FILENAME = 'src/fk/tests/fixtures/flowkeeper-data-TEMP.txt'


class TestFileEventSource(TestCase):
    settings: AbstractSettings
    source: FileEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        self.settings = MockSettings(filename=TEMP_FILENAME)
        self.source = FileEventSource[Tenant](self.settings, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        os.unlink(TEMP_FILENAME)

    def test_initialize(self):
        self.assertIn('user@local.host', self.data)
        user = self.data['user@local.host']
        self.assertEqual(len(user), 0)

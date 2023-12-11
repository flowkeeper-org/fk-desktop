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

from fk.core.abstract_settings import AbstractSettings
from fk.core.app import App
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.user import User


class TestFileEventSource(TestCase):
    settings: AbstractSettings
    source: FileEventSource
    data: dict[str, User]

    def setUp(self):
        self.settings = MockSettings(
            filename='src/fk/tests/fixtures/flowkeeper-data.txt',
            username='alice@flowkeeper.org'
        )
        self.source = FileEventSource(self.settings, App(self.settings), None)
        self.source.start()
        self.data = self.source.get_data()

    def test_read(self):
        self.assertIn('alice@flowkeeper.org', self.data)
        user = self.data['alice@flowkeeper.org']
        self.assertEqual(len(user), 1)
        backlog = user['123-456-789']
        self.assertEqual(backlog.get_name(), 'Sample backlog')

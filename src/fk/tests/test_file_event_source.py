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
import os
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User

TEMP_FILENAME = 'src/fk/tests/fixtures/flowkeeper-data-TEMP.txt'


class TestFileEventSource(TestCase):
    settings: AbstractSettings
    cryptograph: AbstractCryptograph
    source: FileEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self.settings = MockSettings(filename=TEMP_FILENAME)
        self.cryptograph = FernetCryptograph(self.settings)
        self.source = FileEventSource[Tenant](self.settings, self.cryptograph, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        os.unlink(TEMP_FILENAME)

    def test_initialize(self):
        self.assertIn('user@local.host', self.data)
        user = self.data['user@local.host']
        self.assertEqual(len(user), 0)

    # Tests:
    # - Filesystem watcher
    # - Cryptograph -- create a dedicated unit test for it
    # - Creation from existing strategies (no file read)
    # - Events - SourceMessagesRequested, SourceMessagesProcessed, ...
    # - Events in case of errors
    # - Sequence errors, configurable
    # - Skipping strategies out of order
    # - Mute / don't mute
    # - Create file automatically
    # - Dealing with syntax errors
    # - Ignoring comments and empty lines
    # - Starting with non-1 sequences
    # - Writing strategies to file (close / open)
    # - Repair (various cases)
    # - - Removing duplicates
    # - - Renumber strategies
    # - - Create non-existent users on first reference
    # - - Create non-existent backlogs on first reference
    # - - Create non-existent workitems on first reference
    # - - Removing any invalid strategies
    # - - Creating a backup file
    # - - Don't do anything for "good" files
    # - - Check that it can repair something that won't import
    # - Compress
    # - - Creates a backup file
    # - - Compare dumps of random.txt
    # - - No changes if there are no savings
    # - Method calls like disconnect, send_ping, etc.
    # - Auto-seals last strategy
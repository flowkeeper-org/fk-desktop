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
from collections.abc import Callable
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_serializer import AbstractSerializer, T
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem_strategies import CreateWorkitemStrategy

TEMP_FILENAME = 'src/fk/tests/fixtures/flowkeeper-data-TEMP.txt'
RAND_FILENAME = 'src/fk/tests/fixtures/random.txt'


class FilteringSerializer(AbstractSerializer):
    _another: AbstractSerializer
    _strategy_filter: Callable[[AbstractStrategy], bool]

    def __init__(self, another: AbstractSerializer, strategy_filter: Callable[[AbstractStrategy], bool] = None):
        super().__init__(None, None)
        self._another = another
        self._strategy_filter = strategy_filter

    def serialize(self, s: AbstractStrategy) -> T:
        return self._another.serialize(s)

    def deserialize(self, t: str) -> AbstractStrategy | None:
        s = self._another.deserialize(t)
        if self._strategy_filter is None or self._strategy_filter(s):
            return s


def _create_filtered_source(strategy_filter: Callable[[AbstractStrategy], bool] = None) -> FileEventSource:
    _settings = MockSettings(filename=RAND_FILENAME)
    _settings.set({
        'Source.ignore_errors': 'True',
        'Source.ignore_invalid_sequence': 'True',
    })  # Otherwise we won't be able to start it
    _cryptograph = FernetCryptograph(_settings)
    _source = FileEventSource[Tenant](_settings, _cryptograph, Tenant(_settings))
    # This is a hack to replace SimpleSerializer with a filtering wrapper, but it's ok for a unit test
    _source._serializer = FilteringSerializer(_source._serializer, strategy_filter)
    _source.start()
    return _source


def _test_repair(strategy_filter: Callable[[AbstractStrategy], bool],
                 before: Callable[[FileEventSource], None],
                 after: Callable[[FileEventSource], None]):
    backup_filename = None
    root = logging.getLogger()
    try:
        root.setLevel(logging.FATAL)
        src = _create_filtered_source(strategy_filter)
        before(src)
        log, backup_filename = src.repair()
        src = _create_filtered_source()
        after(src)
    finally:
        root.setLevel(logging.DEBUG)
        if backup_filename is not None:
            os.rename(backup_filename, RAND_FILENAME)


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

    def test_repair_strip_create_backlog(self):
        original = _create_filtered_source()

        def check_after_repair(src: FileEventSource):
            self.assertEqual(len(list(original.backlogs())), len(list(src.backlogs())))
            user: User = src.get_data().get_current_user()
            for b in original.backlogs():
                self.assertIsNotNone(user.get(b.get_uid()))
                self.assertEqual(len(user.get(b.get_uid()).values()), len(b.values()))

        _test_repair(lambda s: not isinstance(s, CreateBacklogStrategy),
                     lambda src: self.assertEqual(0, len(list(src.backlogs()))),
                     check_after_repair)

    def test_repair_strip_create_workitem(self):
        original = _create_filtered_source()

        def check_after_repair(src: FileEventSource):
            user: User = src.get_data().get_current_user()
            orphans_list = list(filter(lambda b: b.get_name() == '[Repaired] Orphan workitems', src.backlogs()))
            self.assertEqual(1, len(orphans_list))
            orphans = orphans_list[0]

            # First, check that none of the backlogs have workitems anymore
            for b in src.backlogs():
                if b != orphans:
                    self.assertEqual(0, len(b.values()))

            # Now make sure all WIs are in the orphans instead
            for w in original.workitems():
                self.assertIn(w.get_uid(), orphans)
                self.assertEqual(len(w), len(orphans[w.get_uid()])) # All pomodoros are still there

        _test_repair(lambda s: not isinstance(s, CreateWorkitemStrategy),
                     lambda src: self.assertEqual(len(list(original.backlogs())), len(list(src.backlogs()))),
                     check_after_repair)

    def test_repair_no_op(self):
        original = _create_filtered_source()
        _test_repair(lambda s: True,
                     lambda src: self.assertEqual(original.get_data().get_current_user().dump(), src.get_data().get_current_user().dump()),
                     lambda src: self.assertEqual(original.get_data().get_current_user().dump(), src.get_data().get_current_user().dump()))

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
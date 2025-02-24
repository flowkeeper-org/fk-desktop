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
import os
from pathlib import Path
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.event_source_factory import EventSourceFactory
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.file_event_source import FileEventSource
from fk.core.import_export import import_, export, import_github_issues, import_simple
from fk.core.interruption import Interruption
from fk.core.mock_settings import MockSettings
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import AddPomodoroStrategy, AddInterruptionStrategy
from fk.core.tags import Tags
from fk.core.tenant import Tenant
from fk.core.timer_data import TimerData
from fk.core.timer_strategies import StartTimerStrategy
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy
from fk.tests.test_utils import epyc

TEMP_DIR = 'src/fk/tests/fixtures/'
TEMP_FILE = 'flowkeeper-data-TEMP.txt'
TEMP_FILENAME = f'{TEMP_DIR}{TEMP_FILE}'
EXPORTED_FILENAME = f'{TEMP_DIR}{TEMP_FILE}-exported'
RAND_FILENAME = 'src/fk/tests/fixtures/random.txt'
RAND_DUMP_FILENAME = 'src/fk/tests/fixtures/random-dump.txt'


def _skip_first(dump: str, skip_rows: int) -> str:
    return '\n'.join(dump.split('\n')[skip_rows:])


class TestImportExport(TestCase):
    settings_temp: AbstractSettings
    cryptograph_temp: AbstractCryptograph
    source_temp: FileEventSource
    data_temp: dict[str, User]

    settings_rand: AbstractSettings
    cryptograph_rand: AbstractCryptograph
    source_rand: FileEventSource
    data_rand: dict[str, User]

    def _init_source_temp(self):
        self.source_temp = FileEventSource[Tenant](self.settings_temp, self.cryptograph_temp, Tenant(self.settings_temp))
        self.source_temp.start()
        self.data_temp = self.source_temp.get_data()

    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        self.settings_temp = MockSettings(filename=TEMP_FILENAME)
        self.cryptograph_temp = FernetCryptograph(self.settings_temp)
        self._init_source_temp()

        self.settings_rand = MockSettings(filename=RAND_FILENAME)
        self.cryptograph_rand = FernetCryptograph(self.settings_rand)
        self.source_rand = FileEventSource[Tenant](self.settings_rand, self.cryptograph_rand, Tenant(self.settings_rand))
        self.source_rand.start()
        self.data_rand = self.source_rand.get_data()

        # Needed by smart import
        self._register_source_producers()

    def tearDown(self) -> None:
        for p in Path(TEMP_DIR).glob(f'{TEMP_FILE}*'):
            p.unlink()

    def _register_source_producers(self):
        def ephemeral_source_producer(settings: AbstractSettings, cryptograph: AbstractCryptograph, root: Tenant):
            # This is not 100% accurate, as the original wraps it into a ThreadedEventSource, but should suffice
            # for the purpose of this unit test
            return EphemeralEventSource[Tenant](settings, cryptograph, root)

        EventSourceFactory.get_event_source_factory().register_producer('ephemeral', ephemeral_source_producer)

    def test_initialize(self):
        self.assertIn('user@local.host', self.data_temp)
        user_temp = self.data_temp['user@local.host']
        self.assertEqual(len(user_temp), 0)

        self.assertIn('user@local.host', self.data_rand)
        user_rand = self.data_rand['user@local.host']
        self.assertEqual(len(user_rand), 21)

        dump = user_rand.dump()
        with open(RAND_DUMP_FILENAME, encoding='UTF-8') as f:
            self.assertEqual(f.read(), dump)

    def _execute_import(self, ignore_errors: bool, merge: bool, repair: bool = True, filename: str = None) -> (int, int):
        total_start = 0

        def set_total_start(total):
            nonlocal total_start
            total_start = total

        total_end = 0

        def finish(total):
            nonlocal total_end
            total_end = total
            if repair:
                self.source_temp.repair()
                self._init_source_temp()

        def nothing(*args):
            pass

        import_(self.source_temp,
                RAND_FILENAME if filename is None else filename,
                ignore_errors,
                merge,
                set_total_start,
                nothing,
                finish)

        return total_start, total_end

    def _execute_export(self, compress: bool, filename: str) -> (int, int):
        total_start = 0

        def set_total_start(total):
            nonlocal total_start
            total_start = total

        total_end = 0

        def finish(total):
            nonlocal total_end
            total_end = total

        def nothing(*args):
            pass

        export(self.source_rand,
               filename,
               Tenant(self.settings_rand),
               False,
               compress,
               set_total_start,
               nothing,
               finish)

        return total_start, total_end

    def test_import_classic_ok(self):
        total_start, total_end = self._execute_import(False, False)
        self.assertEqual(total_start, total_end)
        self.assertEqual(total_end, 875)    # That's how many strategies are in random.txt

        # We skip the first 7 lines, as the existing user is kept
        dump_imported = _skip_first(self.data_temp['user@local.host'].dump(), 7)
        dump_original = _skip_first(self.data_rand['user@local.host'].dump(), 7)
        self.assertEqual(dump_imported, dump_original)

    def test_import_classic_twice_error(self):
        self._execute_import(False, False)
        self.assertRaises(Exception, self._execute_import, [False, False])

    def test_import_classic_twice_ignore_errors(self):
        self._execute_import(False, False)
        self._execute_import(True, False)

        # We expect to have all the same backlogs and workitems, but random number of pomodoros in them
        user_temp = self.data_temp['user@local.host']
        user_rand = self.data_rand['user@local.host']
        self.assertEqual(len(user_temp), len(user_rand))
        for b in user_temp:
            backlog_temp = user_temp[b]
            backlog_rand = user_rand[b]
            self.assertEqual(backlog_temp.get_name(), backlog_rand.get_name())
            for w in backlog_temp:
                workitem_temp = backlog_temp[w]
                workitem_rand = backlog_rand[w]
                self.assertEqual(workitem_temp.get_name(), workitem_rand.get_name())

    def _compare_imported_and_original_dumps(self):
        # We skip the first 7 lines, as the existing user is kept
        dump_imported = _skip_first(self.data_temp['user@local.host'].dump(), 7)
        dump_original = _skip_first(self.data_rand['user@local.host'].dump(), 7)
        self.assertEqual(dump_imported, dump_original)

    def test_import_smart_ok(self):
        total_start, total_end = self._execute_import(False, True)
        self.assertEqual(total_end, 874)
        self._compare_imported_and_original_dumps()

    def test_import_smart_twice_ok(self):
        self._execute_import(False, False)
        self._execute_import(False, True)
        self._compare_imported_and_original_dumps()

    def test_import_classic_in_halves_correct_order(self):
        fn1 = f'{RAND_FILENAME}-1'
        fn2 = f'{RAND_FILENAME}-2'
        try:
            # 1. Split the file in two halves
            with open(RAND_FILENAME, encoding='UTF-8') as r:
                i = 0
                with open(fn1, 'w', encoding='UTF-8') as w1, open(fn2, 'w', encoding='UTF-8') as w2:
                    for line in r:
                        if i == 0:
                            w2.write(line)
                        if i < 300:
                            w1.write(line)
                        else:
                            w2.write(line)
                        i += 1

            # 2. Import them
            self._execute_import(False, False, False, fn1)
            self._execute_import(False, False, False, fn2)
            self._compare_imported_and_original_dumps()
        except Exception as e:
            raise e
        finally:
            os.unlink(fn1)
            os.unlink(fn2)

    def test_export_simple_ok(self):
        total_start, total_end = self._execute_export(False, EXPORTED_FILENAME)
        self.assertEqual(total_start, 876)
        self.assertEqual(total_end, total_start)

        self._execute_import(False, False, filename=EXPORTED_FILENAME)

        # We skip the first 7 lines, as the existing user is kept
        dump_imported = _skip_first(self.data_temp['user@local.host'].dump(), 7)
        dump_original = _skip_first(self.data_rand['user@local.host'].dump(), 7)
        self.assertEqual(dump_imported, dump_original)

    def test_export_compressed_ok(self):
        total_start, total_end = self._execute_export(True, EXPORTED_FILENAME)
        self.assertEqual(total_start, 876)
        self.assertEqual(total_end, total_start)

        self._execute_import(False, False, filename=EXPORTED_FILENAME)

        # We skip the first 7 lines, as the existing user is kept
        dump_imported = _skip_first(self.data_temp['user@local.host'].dump(), 7)
        dump_original = _skip_first(self.data_rand['user@local.host'].dump(), 7)
        self.assertEqual(dump_imported, dump_original)

    def test_import_github_ok(self):
        issues = [{
            'number': 101,
            'title': 'Title 101',
            'user': {
                'login': 'user101',
            },
            'assignee': {
                'login': 'assignee101',
            },
            'labels': [
                {'name': 'label101'},
            ],
            'milestone': {
                'title': 'milestone101',
            },
            'state': 'new',
        }, {
            'number': 102,
            'title': 'Title 102',
            'user': {
                'login': 'user101',
            },
            'assignee': {
                'login': 'assignee101',
            },
            'labels': [
                {'name': 'label101'},
            ],
            'milestone': {
                'title': 'milestone101',
            },
            'state': 'new',
        }]
        import_github_issues(self.source_temp,
                             'github',
                             issues,
                             True,
                             True,
                             True,
                             True,
                             True)
        user: User = self.data_temp.get_current_user()

        tags: Tags = user.get_tags()
        self.assertIn('user101', tags)
        self.assertIn('assignee101', tags)
        self.assertIn('label101', tags)
        self.assertIn('milestone101', tags)
        self.assertIn('new', tags)

        backlog: Backlog = user.values()[0]
        self.assertEqual(backlog.get_name(), 'github')

        names = backlog.names()
        self.assertEqual(len(names), 2)
        for n in names:
            self.assertTrue(n.startswith('101 - Title 101') or n.startswith('102 - Title 102'))

    def test_import_simple_ok(self):
        tasks = {
            'b1': [['Title 101', 'new'],
                   ['Title 102', 'completed']],
            'b2': [['Title 201', 'new']],
        }
        import_simple(self.source_temp, tasks)
        user: User = self.data_temp.get_current_user()

        self.assertEqual(len(user), 2)
        for backlog in user.values():
            self.assertTrue(backlog.get_name() == 'b1' or backlog.get_name() == 'b2')
            wi_names = backlog.names()
            if backlog.get_name() == 'b1':
                self.assertEqual(len(wi_names), 2)
                self.assertIn('Title 101', wi_names)
                self.assertIn('Title 102', wi_names)
                for workitem in backlog.values():
                    if workitem.get_name() == 'Title 101':
                        self.assertFalse(workitem.is_sealed())
                    else:
                        self.assertTrue(workitem.is_sealed())
            else:
                self.assertEqual(len(wi_names), 1)
                self.assertIn('Title 201', wi_names)
                workitem: Workitem = backlog.values()[0]
                self.assertFalse(workitem.is_sealed())

    def test_backlog_to_json(self):
        when = epyc()

        # Check user
        user = self.data_temp['user@local.host']
        d = user.to_dict()
        self.assertEqual(len(d), 5)
        self.assertEqual(d['is_system_user'], False)
        self.assertEqual(d['name'], 'Local User')
        self.assertEqual(d['uid'], user.get_uid())
        self.assertEqual(d['create_date'], user.get_create_date())
        self.assertEqual(d['last_modified_date'], user.get_last_modified_date())

        # Check backlog
        self.source_temp.execute(CreateBacklogStrategy,
                                 ['b1', 'First backlog'], True, when)
        backlog: Backlog = user['b1']
        d = backlog.to_dict()
        self.assertEqual(len(d), 5)
        self.assertEqual(d['date_work_started'], None)
        self.assertEqual(d['name'], 'First backlog')
        self.assertEqual(d['uid'], backlog.get_uid())
        self.assertEqual(d['create_date'], when)
        self.assertEqual(d['last_modified_date'], when)

        # Check workitem
        self.source_temp.execute(CreateWorkitemStrategy,
                                 ['w1', backlog.get_uid(), 'Item #one'], True, when)
        workitem: Workitem = backlog['w1']
        d = workitem.to_dict()
        self.assertEqual(len(d), 7)
        self.assertEqual(d['date_work_started'], None)
        self.assertEqual(d['date_work_ended'], None)
        self.assertEqual(d['state'], 'new')
        self.assertEqual(d['name'], 'Item #one')
        self.assertEqual(d['uid'], workitem.get_uid())
        self.assertEqual(d['create_date'], when)
        self.assertEqual(d['last_modified_date'], when)

        # Check pomodoro
        self.source_temp.execute(AddPomodoroStrategy,
                                 ['w1', '1', 'normal'], True, when)
        pomodoro: Pomodoro = workitem.values()[0]
        d = pomodoro.to_dict()
        self.assertEqual(len(d), 12)
        self.assertEqual(d['is_planned'], True)
        self.assertEqual(d['state'], 'new')
        self.assertEqual(d['type'], 'normal')
        self.assertEqual(d['work_duration'], 1500)
        self.assertEqual(d['rest_duration'], 300)
        self.assertEqual(d['date_work_started'], None)
        self.assertEqual(d['date_rest_started'], None)
        self.assertEqual(d['date_completed'], None)
        self.assertEqual(d['name'], 'Pomodoro 1')
        self.assertEqual(d['uid'], pomodoro.get_uid())
        self.assertEqual(d['create_date'], when)
        self.assertEqual(d['last_modified_date'], when)

        # Check interruption
        self.source_temp.execute(StartTimerStrategy,
                                 ['w1', '1500', '300'], True, when)
        self.source_temp.execute(AddInterruptionStrategy,
                                 ['w1', 'good reason', '15'], True, when)
        interruption: Interruption = pomodoro.values()[0]
        d = interruption.to_dict()
        self.assertEqual(len(d), 6)
        self.assertEqual(d['reason'], 'good reason')
        self.assertEqual(d['duration'], datetime.timedelta(seconds=15))
        self.assertEqual(d['void'], False)
        self.assertEqual(d['uid'], interruption.get_uid())
        self.assertEqual(d['create_date'], when)
        self.assertEqual(d['last_modified_date'], when)

        # Check timer
        timer: TimerData = user.get_timer()
        d = timer.to_dict()
        self.assertEqual(len(d), 9)
        self.assertEqual(d['state'], 'work')
        self.assertEqual(d['pomodoro'], pomodoro.get_uid())
        self.assertEqual(d['planned_duration'], 1500)
        self.assertEqual(d['remaining_duration'], 1500)
        self.assertEqual(d['last_state_change'], when)
        self.assertEqual(d['next_state_change'], when + datetime.timedelta(seconds=1500))
        self.assertEqual(d['uid'], timer.get_uid())
        self.assertEqual(d['create_date'], user.get_create_date())
        self.assertEqual(d['last_modified_date'], timer.get_last_modified_date())

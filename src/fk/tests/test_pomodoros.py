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

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.mock_settings import MockSettings
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, RenameWorkitemStrategy, DeleteWorkitemStrategy, \
    CompleteWorkitemStrategy


class TestPomodoros(TestCase):
    settings: AbstractSettings
    cryptograph: AbstractCryptograph
    source: EphemeralEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        self.settings = MockSettings()
        self.cryptograph = FernetCryptograph(self.settings)
        self.source = EphemeralEventSource[Tenant](self.settings, self.cryptograph, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        self.source.dump()

    def _assert_workitem(self, workitem1: Workitem, user: User, backlog: Backlog):
        self.assertEqual(workitem1.get_name(), 'First workitem')
        self.assertEqual(workitem1.get_uid(), 'w11')
        self.assertEqual(workitem1.get_parent(), backlog)
        self.assertEqual(workitem1.get_owner(), user)
        self.assertFalse(workitem1.is_running())
        self.assertFalse(workitem1.is_sealed())
        self.assertFalse(workitem1.is_startable())
        self.assertFalse(workitem1.has_running_pomodoro())
        self.assertTrue(workitem1.is_planned())
        self.assertEqual(len(workitem1.values()), 0)
        
    def _standard_backlog(self) -> (User, Backlog): 
        self.source.execute(CreateBacklogStrategy, ['b1', 'First backlog'])
        user = self.data['user@local.host']
        backlog = user['b1']
        return user, backlog

    def _standard_workitem(self) -> (User, Backlog, Workitem):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        workitem = backlog['w11']
        return user, backlog, workitem

    # Tests:
    # - Sealing pomodoros
    # - Planned time in current state, for different states
    # - Remaining --//--
    # - Total planned time, end of work, end of rest
    # - Start work
    #   - Sealed workitem, non-existing workitem
    #   - Another pomodoro is running
    #   - Non-standard durations overwrite original values
    # - Start rest
    #   - Call explicitly
    #   - Called by Timer
    #   - Sealed workitem, non-existing workitem
    # - Add pomodoro, remove
    #   - Sealed workitem, non-existing workitem
    #   - Invalid number of pomodoros
    #   - Check number of pomodoros added / removed
    #   - Check that add / remove acts as a stack
    # - Finish work, void current
    #   - Sealed workitem, non-existing workitem
    #   - Workitem is not running
    #   - Only affects the running pomodoro
    # - Last modified dates on any Pomodoro changes propagate to the root
    # - Iterate through all pomodoros from event source level
    # - Events

    def test_add_pomodoro(self):
        user, backlog, workitem = self._standard_workitem()
        now = datetime.datetime.now(datetime.timezone.utc)
        then = now - datetime.timedelta(minutes=3)
        self.source.execute(AddPomodoroStrategy, ['w11', '1'], when=then)
        self.source.execute(AddPomodoroStrategy, ['w11', '2'], when=then)
        self.assertEqual(3, len(workitem))
        self.assertFalse(workitem.has_running_pomodoro())
        self.assertIsNone(workitem.get_running_pomodoro())
        incomplete = list[Pomodoro](workitem.get_incomplete_pomodoros())
        self.assertEqual(3, len(incomplete))
        for pomodoro in incomplete:
            self.assertEqual(True, pomodoro.is_startable())
            self.assertEqual(False, pomodoro.is_running())
            self.assertEqual(False, pomodoro.is_working())
            self.assertEqual(False, pomodoro.is_finished())
            self.assertEqual(False, pomodoro.is_resting())
            self.assertEqual(workitem, pomodoro.get_parent())
            self.assertEqual(workitem.get_owner(), pomodoro.get_owner())
            self.assertEqual(300, pomodoro.get_rest_duration())
            self.assertEqual(1500, pomodoro.get_work_duration())
            self.assertEqual(pomodoro.get_create_date(), pomodoro.get_last_modified_date())
            self.assertEqual(then, pomodoro.get_create_date())
            self.assertIsNone(pomodoro.get_rest_start_date())
            self.assertIsNone(pomodoro.get_work_start_date())
            self.assertEqual('new', pomodoro.get_state())
            self.assertEqual(0, pomodoro.total_remaining_time(now))
            self.assertIsNone(pomodoro.planned_end_of_rest())
            self.assertIsNone(pomodoro.planned_end_of_work())
            self.assertEqual(0, pomodoro.planned_time_in_current_state())
            self.assertEqual(0, pomodoro.remaining_time_in_current_state(now))
            self.assertEqual('N/A', pomodoro.remaining_minutes_in_current_state_str(now))
            self.assertIsNotNone(pomodoro.get_uid())
        self.assertNotEqual(incomplete[0].get_uid(), incomplete[1].get_uid())

    def test_add_pomodoro_errors(self):
        user, backlog, workitem = self._standard_workitem()
        self.source.execute(AddPomodoroStrategy, ['w11', '1'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(AddPomodoroStrategy,
                                                      ['w11', '0']))
        self.assertRaises(Exception,
                          lambda: self.source.execute(AddPomodoroStrategy,
                                                      ['w11', '-1']))
        self.assertRaises(Exception,
                          lambda: self.source.execute(AddPomodoroStrategy,
                                                      ['notfound', '1']))
        self.source.execute(AddPomodoroStrategy, ['w11', '20'])

        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])

        self.assertRaises(Exception,
                          lambda: self.source.execute(AddPomodoroStrategy,
                                                      ['w11', '1']))

    def test_remove_pomodoro_errors(self):
        user, backlog, workitem = self._standard_workitem()
        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['w11', '1']))
        self.source.execute(AddPomodoroStrategy, ['w11', '3'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['w11', '0']))
        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['w11', '-1']))
        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['w11', '4']))
        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['notfound', '1']))

        self.source.execute(RemovePomodoroStrategy, ['w11', '1'])
        self.assertEqual(2, len(workitem))
        self.source.execute(RemovePomodoroStrategy, ['w11', '2'])
        self.assertEqual(0, len(workitem))

        self.source.execute(AddPomodoroStrategy, ['w11', '1'])

        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])

        self.assertRaises(Exception,
                          lambda: self.source.execute(RemovePomodoroStrategy,
                                                      ['w11', '1']))

    def test_add_remove_stack(self):
        user, backlog, workitem = self._standard_workitem()
        self.source.execute(AddPomodoroStrategy, ['w11', '3'])
        [p1, p2, p3] = list[Pomodoro](workitem.values())

        self.source.execute(RemovePomodoroStrategy, ['w11', '1'])
        pomodoros = list(workitem.values())
        self.assertEqual(2, len(pomodoros))
        self.assertEqual(pomodoros[0], p1)
        self.assertEqual(pomodoros[1], p2)

        self.source.execute(AddPomodoroStrategy, ['w11', '1'])
        pomodoros = list(workitem.values())
        self.assertEqual(3, len(pomodoros))
        self.assertEqual(pomodoros[0], p1)
        self.assertEqual(pomodoros[1], p2)
        p3 = pomodoros[2]

        self.source.execute(RemovePomodoroStrategy, ['w11', '2'])
        pomodoros = list(workitem.values())
        self.assertEqual(1, len(pomodoros))
        self.assertEqual(pomodoros[0], p1)

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
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.mock_settings import MockSettings
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL, POMODORO_TYPE_TRACKER
from fk.core.pomodoro_strategies import AddPomodoroStrategy, RemovePomodoroStrategy
from fk.core.tenant import Tenant
from fk.core.timer_data import TimerData
from fk.core.timer_strategies import StartTimerStrategy
from fk.core.user import User
from fk.core.user_strategies import AutoSealInternalStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, RenameWorkitemStrategy, CompleteWorkitemStrategy
from fk.tests.test_utils import epyc


class TestPomodoros(TestCase):
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

    def _standard_pomodoro(self, n: int, type: str = POMODORO_TYPE_NORMAL) -> (User, Backlog, Workitem, Pomodoro):
        user, backlog, workitem = self._standard_workitem()
        self.source.execute(AddPomodoroStrategy, ['w11', str(n), type])
        return user, backlog, workitem, workitem.values()

    # Tests:
    # + Sealing pomodoros
    # - pomodoro.seal()
    # + Planned time in current state, for different states
    # + Remaining --//--
    # + Total planned time, end of work, end of rest
    # - Start work
    #   - Sealed workitem, non-existing workitem
    #   - Another pomodoro is running
    #   - Non-standard durations overwrite original values
    # - Start rest
    #   - Call explicitly
    #   - Called by Timer
    #   - Sealed workitem, non-existing workitem
    # + Add pomodoro, remove
    #   + Successful case
    #   + Sealed workitem, non-existing workitem
    #   + Invalid number of pomodoros
    #   + Check number of pomodoros added / removed
    #   + Check that add / remove acts as a stack
    # - Finish work, void current
    #   - Sealed workitem, non-existing workitem
    #   - Workitem is not running
    #   - Only affects the running pomodoro
    # - Interruptions (TODO)
    # - Last modified dates on any Pomodoro changes propagate to the root
    # - Iterate through all pomodoros from event source level
    # - Events
    # - Update remaining duration
    # - To string

    def test_add_pomodoro(self):
        user, backlog, workitem = self._standard_workitem()
        now = datetime.datetime.now(datetime.timezone.utc)
        then = now - datetime.timedelta(minutes=3)
        self.source.execute(AddPomodoroStrategy, ['w11', '1'], when=then)
        self.source.execute(AddPomodoroStrategy, ['w11', '2'], when=then)
        self.assertEqual(3, len(workitem))
        self.assertFalse(workitem.has_running_pomodoro())
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
            self.assertIsNone(pomodoro.planned_end_of_rest())
            self.assertIsNone(pomodoro.planned_end_of_work())
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

    def _assert_pomodoro_and_timer(self,
                                   pomodoro: Pomodoro,
                                   state: str,
                                   when: datetime.datetime,
                                   elapsed: int,
                                   elapsed_str: str = '',
                                   remaining_str: str = '',
                                   remaining_in_state_str: str = ''):
        self.assertIn(state, ['idle', 'work', 'rest', 'finished'])
        timer: TimerData = pomodoro.get_timer()
        timer.update_remaining_duration(when)
        if state == 'idle':
            self.assertTrue(pomodoro.is_startable())
            self.assertFalse(pomodoro.is_running())
            self.assertFalse(pomodoro.is_resting())
            self.assertFalse(pomodoro.is_working())
            self.assertFalse(pomodoro.is_finished())
            self.assertIsNone(pomodoro.get_work_start_date())
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                self.assertIsNone(pomodoro.get_rest_start_date())
                self.assertIsNone(pomodoro.planned_end_of_rest())
                self.assertEqual(pomodoro.remaining_time_in_current_state(when), 0)
                self.assertIsNone(pomodoro.planned_end_of_work())
                self.assertEqual(pomodoro.remaining_minutes_in_current_state_str(when), "N/A")
            self.assertTrue(timer.is_idling())
            self.assertFalse(timer.is_ticking())
            self.assertFalse(timer.is_working())
            self.assertFalse(timer.is_resting())
            self.assertEqual(timer.get_planned_duration(), 0)
            self.assertEqual(timer.get_remaining_duration(), 0)
            self.assertEqual(timer.format_elapsed_duration(when), "N/A")
            self.assertEqual(timer.format_remaining_duration(), "00:00")
        elif state == 'work':
            self.assertFalse(pomodoro.is_startable())
            self.assertTrue(pomodoro.is_running())
            self.assertFalse(pomodoro.is_resting())
            self.assertTrue(pomodoro.is_working())
            self.assertFalse(pomodoro.is_finished())
            self.assertIsNotNone(pomodoro.get_work_start_date())
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                self.assertIsNone(pomodoro.get_rest_start_date())
                self.assertEqual(pomodoro.planned_end_of_work(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1500))
                self.assertEqual(pomodoro.planned_end_of_rest(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1800))
                self.assertEqual(pomodoro.remaining_time_in_current_state(when), 1500 - elapsed)
                self.assertEqual(timer.get_planned_duration(), 1500)
                self.assertEqual(timer.get_remaining_duration(), 1500 - elapsed)
                self.assertEqual(timer.format_remaining_duration(), remaining_str)
                self.assertEqual(pomodoro.remaining_minutes_in_current_state_str(when), remaining_in_state_str)
            self.assertEqual(timer.format_elapsed_duration(when), elapsed_str)
            self.assertFalse(timer.is_idling())
            self.assertTrue(timer.is_ticking())
            self.assertTrue(timer.is_working())
            self.assertFalse(timer.is_resting())
        elif state == 'rest':
            self.assertFalse(pomodoro.is_startable())
            self.assertTrue(pomodoro.is_running())
            self.assertTrue(pomodoro.is_resting())
            self.assertFalse(pomodoro.is_working())
            self.assertFalse(pomodoro.is_finished())
            self.assertIsNotNone(pomodoro.get_work_start_date())
            self.assertEqual(pomodoro.get_type(), POMODORO_TYPE_NORMAL)
            self.assertIsNotNone(pomodoro.get_rest_start_date())
            self.assertEqual(pomodoro.planned_end_of_work(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1500))
            self.assertEqual(pomodoro.planned_end_of_rest(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1800))
            self.assertEqual(pomodoro.remaining_time_in_current_state(when), 1800 - elapsed)
            self.assertFalse(timer.is_idling())
            self.assertTrue(timer.is_ticking())
            self.assertFalse(timer.is_working())
            self.assertTrue(timer.is_resting())
            self.assertEqual(timer.get_planned_duration(), 300)
            self.assertEqual(timer.get_remaining_duration(), 1800 - elapsed)
            self.assertEqual(timer.format_elapsed_duration(when), elapsed_str)
            self.assertEqual(timer.format_remaining_duration(), remaining_str)
            self.assertEqual(pomodoro.remaining_minutes_in_current_state_str(when), remaining_in_state_str)
        elif state == 'finished':
            self.assertFalse(pomodoro.is_startable())
            self.assertFalse(pomodoro.is_running())
            self.assertFalse(pomodoro.is_resting())
            self.assertFalse(pomodoro.is_working())
            self.assertTrue(pomodoro.is_finished())
            self.assertIsNotNone(pomodoro.get_work_start_date())
            if pomodoro.get_type() == POMODORO_TYPE_NORMAL:
                self.assertIsNotNone(pomodoro.get_rest_start_date())
                self.assertEqual(pomodoro.planned_end_of_rest(), pomodoro.get_last_modified_date())
                self.assertEqual(pomodoro.planned_end_of_work(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1500))
                self.assertEqual(pomodoro.planned_end_of_rest(), pomodoro.get_work_start_date() + datetime.timedelta(seconds=1800))
                self.assertEqual(pomodoro.remaining_time_in_current_state(when), 0)
                self.assertEqual(timer.format_remaining_duration(), "00:00")
                self.assertEqual(pomodoro.remaining_minutes_in_current_state_str(when), "N/A")
            self.assertTrue(timer.is_idling())
            self.assertFalse(timer.is_ticking())
            self.assertFalse(timer.is_working())
            self.assertFalse(timer.is_resting())
            self.assertEqual(timer.get_planned_duration(), 0)
            self.assertEqual(timer.get_remaining_duration(), 0)
            self.assertEqual(timer.format_elapsed_duration(when), "N/A")

    def test_planned_unplanned_pomodoro(self):
        _, _, workitem, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        self.source.execute(AddPomodoroStrategy, ['w11', '1', POMODORO_TYPE_NORMAL], True, when)
        [p1, p2] = workitem.values()
        self.assertTrue(p1.is_planned())
        self.assertFalse(p2.is_planned())

    def test_start_work_normal_ok(self):
        user, _, workitem, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self._assert_pomodoro_and_timer(pomodoro, 'idle', when, 0)
        self.assertEqual(user.get_state(when), ('Idle', 0))
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        self._assert_pomodoro_and_timer(pomodoro, 'work', when, 0, "0:00:00", "25:00", "25 minutes")
        self.assertEqual(user.get_state(when), ('Focus', "25 minutes"))

    def test_start_work_tracker_ok(self):
        user, _, workitem, [pomodoro] = self._standard_pomodoro(1, POMODORO_TYPE_TRACKER)
        when = epyc()
        self._assert_pomodoro_and_timer(pomodoro, 'idle', when, 0)
        self.source.execute(StartTimerStrategy, ['w11'], True, when)
        self._assert_pomodoro_and_timer(pomodoro, 'work', when, 0, "0:00:00")
        self.assertEqual(user.get_state(when), ('Tracking', 0))

    def test_start_work_tracker_raises(self):
        _, _, workitem, [pomodoro] = self._standard_pomodoro(1, POMODORO_TYPE_TRACKER)
        self.assertRaises(Exception, lambda: pomodoro.get_rest_start_date())
        self.assertRaises(Exception, lambda: pomodoro.get_rest_duration())
        self.assertRaises(Exception, lambda: pomodoro.planned_end_of_rest())
        self.assertRaises(Exception, lambda: pomodoro.planned_end_of_work())
        self.assertRaises(Exception, lambda: pomodoro.get_rest_duration())
        self.assertRaises(Exception, lambda: pomodoro.update_rest_duration(1))
        self.assertRaises(Exception, lambda: pomodoro.remaining_time_in_current_state(epyc()))
        self.assertRaises(Exception, lambda: pomodoro.remaining_minutes_in_current_state_str(epyc()))

    def test_auto_seal_shortly_from_work(self):
        user, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=1550)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'rest', when, 1550, "0:25:50", "04:10", "4 minutes")
        self.assertEqual(user.get_state(when), ('Rest', "4 minutes"))

    def test_auto_seal_shortly_from_rest(self):
        _, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=1550)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        when += datetime.timedelta(seconds=300)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'finished', when, 1850)

    def test_auto_seal_long_after_from_work(self):
        user, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=1850)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'finished', when, 1850)
        self.assertEqual(user.get_state(when), ('Idle', 0))

    def test_auto_seal_too_early(self):
        _, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=600)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'work', when, 600, "0:10:00", "15:00", "15 minutes")

    def test_auto_seal_twice(self):
        _, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=1550)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'rest', when, 1550, "0:25:50", "04:10", "4 minutes")
        when += datetime.timedelta(seconds=10)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'rest', when, 1560, "0:26:00", "04:00", "4 minutes")

    def test_auto_seal_unneeded(self):
        _, _, _, [pomodoro] = self._standard_pomodoro(1)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11', '1500', '300'], True, when)
        when += datetime.timedelta(seconds=1550)
        self.source.execute(RenameWorkitemStrategy, ['w11', 'New name'], True, when)
        self._assert_pomodoro_and_timer(pomodoro, 'work', when, 1500, "0:25:50", "00:00", "N/A")

    def test_auto_seal_strategies(self):
        # For all strategies check if the pomodoro was auto-sealed
        pass

    def test_auto_seal_tracker(self):
        # No auto-seal for trackers. All other tests use normal pomodoros.
        _, _, _, [pomodoro] = self._standard_pomodoro(1, POMODORO_TYPE_TRACKER)
        when = epyc()
        self.source.execute(StartTimerStrategy, ['w11'], True, when)
        when += datetime.timedelta(seconds=1550)
        self.source.execute(AutoSealInternalStrategy, [], False, when)
        self._assert_pomodoro_and_timer(pomodoro, 'work', when, 1550,  "0:25:50")

    def test_auto_seal_long_break(self):
        # No auto-seal for long breaks. All other tests have short breaks.
        pass


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
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import AddPomodoroStrategy
from fk.core.tenant import Tenant
from fk.core.timer_strategies import StartTimerStrategy
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, RenameWorkitemStrategy, DeleteWorkitemStrategy, \
    CompleteWorkitemStrategy, MoveWorkitemStrategy


class TestWorkitems(TestCase):
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

    def test_create_workitems(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second workitem'])
        self.assertIn('w11', backlog)
        self.assertIn('w12', backlog)
        workitem1: Workitem = backlog['w11']
        self._assert_workitem(workitem1, user, backlog)
        workitem2 = backlog['w12']
        self.assertEqual(workitem2.get_name(), 'Second workitem')

    def test_create_workitems_with_tags(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', '#Second workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w13', 'b1', '#Third #workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w14', 'b1', 'Fourth #workitem and some more #workitem text'])
        self.source.execute(CreateWorkitemStrategy, ['w15', 'b1', 'Fifth #workitem.'])
        self.source.execute(CreateWorkitemStrategy, ['w16', 'b1', 'Six #workitem and #workitems'])
        self.assertIn('w11', backlog)
        self.assertIn('w12', backlog)
        self.assertIn('w13', backlog)
        self.assertIn('w14', backlog)
        self.assertIn('w15', backlog)
        self.assertIn('w16', backlog)
        workitem1: Workitem = backlog['w11']
        self._assert_workitem(workitem1, user, backlog)
        workitem2 = backlog['w12']
        self.assertEqual(workitem2.get_name(), '#Second workitem')
        workitem3 = backlog['w13']
        self.assertEqual(workitem3.get_name(), '#Third #workitem')
        workitem4 = backlog['w14']
        self.assertEqual(workitem4.get_name(), 'Fourth #workitem and some more #workitem text')
        workitem5 = backlog['w15']
        self.assertEqual(workitem5.get_name(), 'Fifth #workitem.')
        workitem6 = backlog['w16']
        self.assertEqual(workitem6.get_name(), 'Six #workitem and #workitems')
        tags = user.get_tags()
        self.assertEqual(len(tags), 4)
        self.assertIn('workitem', tags)
        self.assertIn('second', tags)
        self.assertIn('third', tags)
        self.assertIn('workitems', tags)
        workitems = tags['workitem'].get_workitems()
        self.assertEqual(len(workitems), 4)
        self.assertIn(workitem3, workitems)
        self.assertIn(workitem4, workitems)
        self.assertIn(workitem5, workitems)
        self.assertIn(workitem6, workitems)

    def test_execute_prepared(self):
        user, backlog = self._standard_backlog()
        s = CreateWorkitemStrategy(2,
                                  datetime.datetime.now(datetime.timezone.utc),
                                  user.get_identity(),
                                  ['w11', 'b1', 'First workitem'],
                                  self.settings)
        self.source.execute_prepared_strategy(s)
        self.assertIn('w11', backlog)
        workitem1: Workitem = backlog['w11']
        self._assert_workitem(workitem1, user, backlog)

    def test_create_duplicate_workitem_failure(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem 1'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem 2']))

    def test_rename_nonexistent_workitem_failure(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second workitem'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(RenameWorkitemStrategy, ['w13', 'Renamed workitem']))

    def test_rename_workitem(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(RenameWorkitemStrategy, ['w11', 'Renamed workitem'])
        self.assertEqual(backlog['w11'].get_name(), 'Renamed workitem')

    def test_delete_nonexistent_workitem_failure(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second workitem'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(DeleteWorkitemStrategy, ['w13']))

    def test_delete_workitem(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second workitem'])
        self.assertIn('w11', backlog)
        self.source.execute(DeleteWorkitemStrategy, ['w11'])
        self.assertNotIn('w11', backlog)
        self.assertIn('w12', backlog)

    def test_complete_workitem_basic(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        workitem = backlog['w11']
        incomplete = list(backlog.get_incomplete_workitems())
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0], workitem)
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertIn('w11', backlog)
        self.assertFalse(workitem.is_startable())
        self.assertTrue(workitem.is_sealed())
        self.assertFalse(workitem.is_running())
        self.assertFalse(workitem.has_running_pomodoro())
        incomplete = list(backlog.get_incomplete_workitems())
        self.assertEqual(len(incomplete), 0)

    def test_complete_workitem_with_two_pomodoros(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(AddPomodoroStrategy, ['w11', '2'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertFalse(backlog['w11'].is_startable())

    def test_complete_workitem_invalid_state(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(CompleteWorkitemStrategy, ['w11', 'invalid']))

    def test_complete_workitem_twice(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished']))

    def test_rename_completed_workitem(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Before'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(RenameWorkitemStrategy, ['w11', 'After']))

    def test_add_pomodoro_to_completed_workitem(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Before'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(AddPomodoroStrategy, ['w11', '1']))

    def test_delete_completed_workitem(self):
        _, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Before'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.source.execute(DeleteWorkitemStrategy, ['w11'])
        self.assertNotIn('w11', backlog)

    def test_start_completed_workitem(self):
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Before'])
        self.source.execute(AddPomodoroStrategy, ['w11', '1'])
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(StartTimerStrategy, ['w11', '1', '1']))

    # Next -- Test all workitem-specific stuff (check coverage)
    # - Lifecycle, including automatic voiding and completion of pomodoros (check all situations)
    # - State -- isStartable based on pomodoros
    # - Isolation between backlogs
    # - That we can find them via the Source
    # - Check update timestamps
    # - Add (2), (3) and (4) to backlogs, too

    def test_events_create_workitem(self):
        fired = list()

        def on_event(event, **kwargs):
            if event not in ('BeforeMessageProcessed', 'AfterMessageProcessed'):
                fired.append(event)
            if event == 'BeforeWorkitemCreate':
                self.assertIn('workitem_uid', kwargs)
                self.assertIn('backlog_uid', kwargs)
                self.assertIn('workitem_name', kwargs)
                self.assertEqual(kwargs['workitem_uid'], 'w11')
                self.assertEqual(kwargs['backlog_uid'], 'b1')
                self.assertEqual(kwargs['workitem_name'], 'First workitem')
            elif event == 'AfterWorkitemCreate':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)

        self._standard_backlog()
        self.source.on('*', on_event)
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.assertEqual(len(fired), 2)
        self.assertEqual(fired[0], 'BeforeWorkitemCreate')
        self.assertEqual(fired[1], 'AfterWorkitemCreate')

    def test_events_delete_workitem(self):
        fired = list()

        def on_event(event, **kwargs):
            if event not in ('BeforeMessageProcessed', 'AfterMessageProcessed'):
                fired.append(event)
            if event == 'BeforeWorkitemDelete' or event == 'AfterWorkitemDelete':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)
                self.assertEqual(kwargs['workitem'].get_name(), 'First item')
            elif event == 'BeforePomodoroVoided' or event == 'AfterPomodoroVoided':
                self.assertIn('pomodoro', kwargs)
                self.assertIn('reason', kwargs)
                self.assertTrue(type(kwargs['pomodoro']) is Pomodoro)
                self.assertEqual(kwargs['pomodoro'].get_parent().get_name(), 'First item')
                self.assertTrue(kwargs['reason'].startswith('Voided automatically'))

        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First item'])
        self.source.execute(AddPomodoroStrategy, ['w11', '2'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second item'])
        self.source.execute(AddPomodoroStrategy, ['w11', '2'])
        self.source.execute(StartTimerStrategy, ['w11', '1', '1'])
        self.source.on('*', on_event)  # We only care about delete here
        self.source.execute(DeleteWorkitemStrategy, ['w11'])
        self.assertEqual(len(fired), 8)
        self.assertEqual(fired[0], 'BeforePomodoroRestStart')
        self.assertEqual(fired[1], 'TimerWorkComplete')
        self.assertEqual(fired[2], 'AfterPomodoroRestStart')
        self.assertEqual(fired[3], 'BeforeWorkitemDelete')
        self.assertEqual(fired[4], 'BeforePomodoroVoided')
        self.assertEqual(fired[5], 'TimerRestComplete')
        self.assertEqual(fired[6], 'AfterPomodoroVoided')
        self.assertEqual(fired[7], 'AfterWorkitemDelete')

    def test_events_complete_workitem(self):
        fired = list()

        def on_event(event, **kwargs):
            if event not in ('BeforeMessageProcessed', 'AfterMessageProcessed'):
                fired.append(event)
            if event == 'BeforeWorkitemComplete' or event == 'AfterWorkitemComplete':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)
                self.assertEqual(kwargs['workitem'].get_name(), 'First item')
            elif event == 'BeforePomodoroVoided' or event == 'AfterPomodoroVoided':
                self.assertIn('pomodoro', kwargs)
                self.assertIn('reason', kwargs)
                self.assertTrue(type(kwargs['pomodoro']) is Pomodoro)
                self.assertEqual(kwargs['pomodoro'].get_parent().get_name(), 'First item')
                self.assertTrue(kwargs['reason'].startswith('Voided automatically'))

        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First item'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second item'])
        self.source.execute(AddPomodoroStrategy, ['w11', '2'])
        self.source.execute(StartTimerStrategy, ['w11', '1', '1'])
        self.source.on('*', on_event)  # We only care about delete here
        self.source.execute(CompleteWorkitemStrategy, ['w11', 'finished'])
        self.assertEqual(len(fired), 10)
        self.assertEqual(fired[0], 'BeforePomodoroRestStart')
        self.assertEqual(fired[1], 'TimerWorkComplete')
        self.assertEqual(fired[2], 'AfterPomodoroRestStart')
        self.assertEqual(fired[3], 'BeforeWorkitemComplete')
        self.assertEqual(fired[4], 'BeforePomodoroInterrupted')
        self.assertEqual(fired[5], 'AfterPomodoroInterrupted')
        self.assertEqual(fired[6], 'BeforePomodoroVoided')
        self.assertEqual(fired[7], 'TimerRestComplete')
        self.assertEqual(fired[8], 'AfterPomodoroVoided')
        self.assertEqual(fired[9], 'AfterWorkitemComplete')

    def test_events_rename_workitem(self):
        fired = list()

        def on_event(event, **kwargs):
            if event not in ('BeforeMessageProcessed', 'AfterMessageProcessed'):
                fired.append(event)
            if event == 'BeforeWorkitemRename' or event == 'AfterWorkitemRename':
                self.assertIn('workitem', kwargs)
                self.assertIn('old_name', kwargs)
                self.assertIn('new_name', kwargs)
                self.assertEqual(kwargs['old_name'], 'Before')
                self.assertEqual(kwargs['new_name'], 'After')
                self.assertTrue(type(kwargs['workitem']) is Workitem)

        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Before'])
        self.source.on('*', on_event)
        self.source.execute(RenameWorkitemStrategy, ['w11', 'After'])
        self.assertEqual(len(fired), 2)
        self.assertEqual(fired[0], 'BeforeWorkitemRename')
        self.assertEqual(fired[1], 'AfterWorkitemRename')

    # Reordering tests:
    # - Positive test -- move up and down
    # - Negative index and index > len()
    # - No move -- up and down
    # - Events

    def _create_workitems_for_reorder_tests(self):
        _, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Second workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w13', 'b1', 'Third workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w14', 'b1', 'Fourth workitem'])
        return backlog

    def _assert_workitem_order(self, backlog: Backlog, order: str):
        pass

    def test_reorder_workitem_up_normal(self):
        backlog = self._create_workitems_for_reorder_tests()
        self._assert_workitem_order(backlog, 'w11,w12,w13,w14')

    def test_move_workitems_ok(self):
        self.source.execute(CreateBacklogStrategy, ['b1', 'Backlog 1'])
        self.source.execute(CreateBacklogStrategy, ['b2', 'Backlog 2'])
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem'])
        self.source.execute(MoveWorkitemStrategy, ['w11', 'b2'])
        user: User = self.data.get_current_user()
        self.assertEqual(len(user['b1']), 0)
        self.assertEqual(len(user['b2']), 1)
        self.assertIn('w11', user['b2'])

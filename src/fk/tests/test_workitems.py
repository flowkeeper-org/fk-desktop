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

from fk.core.abstract_settings import AbstractSettings
from fk.core.workitem import Workitem
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, RenameBacklogStrategy, DeleteBacklogStrategy
from fk.core.workitem_strategies import CreateWorkitemStrategy, RenameWorkitemStrategy, DeleteWorkitemStrategy
from fk.core.pomodoro_strategies import AddPomodoroStrategy
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem


class TestWorkitems(TestCase):
    settings: AbstractSettings
    source: EphemeralEventSource
    data: dict[str, User]

    def setUp(self) -> None:
        self.settings = MockSettings()
        self.source = EphemeralEventSource(self.settings, Tenant(self.settings))
        self.source.start()
        self.data = self.source.get_data()

    def tearDown(self) -> None:
        self.source.dump()

    def _assert_workitem(self, workitem1: Workitem, user: User, backlog: Backlog):
        self.assertEqual(workitem1.get_name(), 'First workitem')
        self.assertEqual(workitem1.get_uid(), 'w11')
        self.assertEqual(workitem1.get_parent(), backlog)
        self.assertEqual(workitem1.get_owner(), user)
        self.assertFalse(workitem1.is_running() or workitem1.is_sealed())
        self.assertFalse(workitem1.has_running_pomodoro())
        self.assertTrue(workitem1.is_planned() and workitem1.is_startable())
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

    def test_execute_prepared(self):
        user, backlog = self._standard_backlog()
        s = CreateWorkitemStrategy(2,
                                  datetime.datetime.now(datetime.timezone.utc),
                                  user,
                                  ['w11', 'b1', 'First workitem'],
                                  self.source._emit,
                                  self.data,
                                  self.settings)
        self.source.execute_prepared_strategy(s)
        self.assertIn('w11', backlog)
        workitem1: Workitem = backlog['w11']
        self._assert_workitem(workitem1, user, backlog)

    def test_create_duplicate_workitem_failure(self):
        user, backlog = self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem 1'])
        self.assertRaises(Exception,
                          lambda: self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'First workitem 2']))

    def test_rename_nonexistent_workitem_failure(self):
        user, backlog = self._standard_backlog()
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
        user, backlog = self._standard_backlog()
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

    # TODO: Test all workitem-specific stuff (check coverage)
    # - Lifecycle
    # - Isolation between backlogs
    # - That we can find them via the Source
    # - Check update timestamps
    # - Add (2), (3) and (4) to backlogs, too

    def test_events_create_workitem(self):
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeWorkitemCreate':
                self.assertIn('workitem_uid', kwargs)
                self.assertIn('backlog_uid', kwargs)
                self.assertIn('workitem_name', kwargs)
                self.assertEquals(kwargs['old_name'], 'Before')
                self.assertEquals(kwargs['new_name'], 'After')
                self.assertTrue(type(kwargs['workitem']) is Workitem)                    
            elif event == 'AfterWorkitemCreate':
                self.assertIn('workitem', kwargs)
                self.assertIn('backlog_uid', kwargs)
                self.assertIn('workitem_name', kwargs)
                self.assertIn('new_name', kwargs)
                self.assertEquals(kwargs['old_name'], 'Before')
                self.assertEquals(kwargs['new_name'], 'After')
                self.assertTrue(type(kwargs['workitem']) is Workitem)                                    
        self.source.execute(CreateWorkitemStrategy, ['123-456-789-1', 'Before'])
        self.source.on('*', on_event)
        self.source.execute(RenameWorkitemStrategy, ['123-456-789-1', 'After'])
        self.assertEquals(len(fired), 4)
        self.assertEquals(fired[0], 'BeforeMessageProcessed')
        self.assertEquals(fired[1], 'BeforeWorkitemRename')
        self.assertEquals(fired[2], 'AfterWorkitemRename')
        self.assertEquals(fired[3], 'AfterMessageProcessed')


    def test_events_delete_workitem(self):
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeWorkitemDelete' or event == 'AfterWorkitemDelete':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)
                self.assertEquals(kwargs['workitem'].get_name(), 'First workitem')
            elif event == 'BeforeWorkitemDelete' or event == 'AfterWorkitemDelete':
                self.assertIn('workitem', kwargs)
                self.assertTrue(type(kwargs['workitem']) is Workitem)
                self.assertIn(kwargs['workitem'].get_name(), ['First item', 'Second item'])
        self.source.execute(CreateWorkitemStrategy, ['123-456-789-1', 'First workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w1', '123-456-789-1', 'First item'])
        self.source.execute(AddPomodoroStrategy, ['w1', '2'])
        self.source.execute(CreateWorkitemStrategy, ['w2', '123-456-789-1', 'Second item'])
        self.source.execute(CreateWorkitemStrategy, ['123-456-789-2', 'Second workitem'])
        self.source.execute(CreateWorkitemStrategy, ['w3', '123-456-789-2', 'Third item'])
        self.source.on('*', on_event)  # We only care about delete here
        self.source.execute(DeleteWorkitemStrategy, ['123-456-789-1'])
        self.assertEquals(len(fired), 12)  # Note that although we had a cascade delete, only one strategy got executed
        # The events must arrive in the right order, too
        self.assertEquals(fired[0], 'BeforeMessageProcessed')
        self.assertEquals(fired[1], 'BeforeWorkitemDelete')
        self.assertEquals(fired[2], 'BeforeMessageProcessed')  # auto=True
        self.assertEquals(fired[3], 'BeforeWorkitemDelete')
        self.assertEquals(fired[4], 'AfterWorkitemDelete')
        self.assertEquals(fired[5], 'AfterMessageProcessed')  # auto=True
        self.assertEquals(fired[6], 'BeforeMessageProcessed')  # auto=True
        self.assertEquals(fired[7], 'BeforeWorkitemDelete')
        self.assertEquals(fired[8], 'AfterWorkitemDelete')
        self.assertEquals(fired[9], 'AfterMessageProcessed')  # auto=True
        self.assertEquals(fired[10], 'AfterWorkitemDelete')
        self.assertEquals(fired[11], 'AfterMessageProcessed')        
        # Automatic voiding of pomodoros will be tested when we cover the lifecycles

    def test_events_rename_workitem(self):
        fired = list()
        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'BeforeWorkitemRename' or event == 'AfterWorkitemRename':
                self.assertIn('workitem', kwargs)
                self.assertIn('old_name', kwargs)
                self.assertIn('new_name', kwargs)
                self.assertEquals(kwargs['old_name'], 'Before')
                self.assertEquals(kwargs['new_name'], 'After')
                self.assertTrue(type(kwargs['workitem']) is Workitem)                    
        self.source.execute(CreateWorkitemStrategy, ['123-456-789-1', 'Before'])
        self.source.on('*', on_event)
        self.source.execute(RenameWorkitemStrategy, ['123-456-789-1', 'After'])
        self.assertEquals(len(fired), 4)
        self.assertEquals(fired[0], 'BeforeMessageProcessed')
        self.assertEquals(fired[1], 'BeforeWorkitemRename')
        self.assertEquals(fired[2], 'AfterWorkitemRename')
        self.assertEquals(fired[3], 'AfterMessageProcessed')

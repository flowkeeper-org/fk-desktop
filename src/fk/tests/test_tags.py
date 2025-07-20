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
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tag import Tag
from fk.core.tags import Tags
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.user_strategies import CreateUserStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, DeleteWorkitemStrategy, RenameWorkitemStrategy


class TestTags(TestCase):
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

    # TODO: Move it to superclass
    def _standard_backlog(self) -> (User, Backlog):
        user = self.data['user@local.host']
        if 'b1' not in user:
            self.source.execute(CreateBacklogStrategy, ['b1', 'First backlog'])
            return user, user['b1']

    def _add_workitem(self, name: str, uid: str = 'w11') -> Workitem:
        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, [uid, 'b1', name])
        return self.data['user@local.host']['b1'][uid]

    def _delete_workitem(self, uid: str) -> None:
        self.source.execute(DeleteWorkitemStrategy, [uid])

    def _rename_workitem(self, uid: str, new_name: str) -> None:
        self.source.execute(RenameWorkitemStrategy, [uid, new_name])

    def tearDown(self) -> None:
        self.source.dump()

    # - Invalid tag names
    def test_create_workitem_without_tags(self):
        user = self.data['user@local.host']
        self._add_workitem('There are no tags', 'w11')
        self._add_workitem('Trying ## x', 'w12')
        self._add_workitem('Trying #. x', 'w13')
        self._add_workitem('Trying # x', 'w14')
        self._add_workitem('# trying', 'w15')
        self._add_workitem('##. another', 'w16')
        self.assertEqual(len(user.get_tags()), 0)

    # - Valid tags (beginning of string, end, only tag, no value, etc.)
    def test_create_workitem_with_tags(self):
        user = self.data['user@local.host']
        self._add_workitem('There is #one tag', 'w11')
        self._add_workitem('There are #two tags #three', 'w12')
        self._add_workitem('There are #four and #four identical tags', 'w13')
        self._add_workitem('#five', 'w14')
        self._add_workitem('#6', 'w15')
        self._add_workitem('And #seven', 'w16')
        self._add_workitem('###eight', 'w17')
        self._add_workitem('# nine', 'w18')
        self._add_workitem('And another #one', 'w19')
        self._add_workitem('#десять', 'w20')
        self._add_workitem('#11eleven11', 'w21')
        self._add_workitem('#twelve_12', 'w22')
        self._add_workitem('#_', 'w23')
        self._add_workitem('#fourteen-14', 'w24')
        self._add_workitem('#fifteen_15', 'w25')
        self._add_workitem('#SIXTEEN', 'w26')
        self._add_workitem('#Sixteen', 'w27')
        tags = user.get_tags()
        self.assertEqual(len(tags), 15)

        self.assertIn('one', tags)
        self.assertIn('two', tags)
        self.assertIn('three', tags)
        self.assertIn('four', tags)
        self.assertIn('five', tags)
        self.assertIn('6', tags)
        self.assertIn('seven', tags)
        self.assertIn('eight', tags)
        self.assertIn('десять', tags)
        self.assertIn('11eleven11', tags)
        self.assertIn('twelve_12', tags)
        self.assertIn('_', tags)
        self.assertIn('fourteen', tags)
        self.assertIn('fifteen_15', tags)
        self.assertIn('sixteen', tags)

    # - DeleteWorkitem
    def test_delete_workitem(self):
        user = self.data['user@local.host']
        self._add_workitem('There is #one tag', 'w11')
        self._add_workitem('There is #another #one', 'w12')
        self._add_workitem('And #another one', 'w13')
        tags = user.get_tags()
        self.assertEqual(len(tags), 2)
        self.assertIn('another', tags)
        self.assertIn('one', tags)

        self._delete_workitem('w11')
        self.assertEqual(len(tags), 2)

        self._delete_workitem('w12')
        self.assertEqual(len(tags), 1)
        self.assertIn('another', tags)

        self._delete_workitem('w13')
        self.assertEqual(len(tags), 0)

    # - RenameWorkitem -- add, delete, no change
    def test_rename_workitem(self):
        user = self.data['user@local.host']
        self._add_workitem('There is #one tag', 'w11')
        self._add_workitem('There is #another #one', 'w12')
        self._add_workitem('And #another one', 'w13')
        tags = user.get_tags()
        self.assertEqual(len(tags), 2)

        self._rename_workitem('w11', '#Third tag')
        self.assertEqual(len(tags), 3)
        self.assertIn('another', tags)
        self.assertIn('one', tags)
        self.assertIn('third', tags)

        self._rename_workitem('w11', 'No tag')
        self.assertEqual(len(tags), 2)
        self.assertIn('another', tags)
        self.assertIn('one', tags)

        self._rename_workitem('w12', 'Also no tags here')
        self.assertEqual(len(tags), 1)
        self.assertIn('another', tags)

        self._rename_workitem('w13', 'Removed all tags')
        self.assertEqual(len(tags), 0)

        self._rename_workitem('w11', 'Added #two #tags')
        self.assertEqual(len(tags), 2)
        self.assertIn('two', tags)
        self.assertIn('tags', tags)

        self._rename_workitem('w11', 'Added #last #tags')
        self.assertEqual(len(tags), 2)
        self.assertIn('last', tags)
        self.assertIn('tags', tags)

        self._rename_workitem('w11', 'Added #last #tags')
        self.assertEqual(len(tags), 2)
        self.assertIn('last', tags)
        self.assertIn('tags', tags)

    # - Tag accessors in event source
    def test_event_source(self):
        user = self.data['user@local.host']
        self._add_workitem('#one #two #three')

        found_one = False
        found_two = False
        found_three = False
        for tag in self.source.tags():
            self.assertIn(tag.get_uid(), ['one', 'two', 'three'])
            if tag.get_uid() == 'one':
                found_one = True
            elif tag.get_uid() == 'two':
                found_two = True
            elif tag.get_uid() == 'three':
                found_three = True
        self.assertTrue(found_one)
        self.assertTrue(found_two)
        self.assertTrue(found_three)

        self.assertIsNotNone(self.source.find_tag('one'))
        self.assertIsNone(self.source.find_tag('four'))
        self.assertEqual(self.source.find_tag('one').get_uid(), 'one')

    # - Reverse workitem accessors
    def test_workitem_accessors(self):
        user = self.data['user@local.host']
        w11 = self._add_workitem('There is #one tag', 'w11')
        w12 = self._add_workitem('There is #another #one', 'w12')
        w13 = self._add_workitem('And #another one', 'w13')
        self._rename_workitem('w11', 'Now it is #another tag')
        self._rename_workitem('w13', '#one here')

        tags = user.get_tags()
        self.assertEqual(len(tags), 2)
        tag_one = tags['one'].get_workitems()
        tag_another = tags['another'].get_workitems()

        self.assertEqual(len(tag_one), 2)
        self.assertEqual(len(tag_another), 2)
        self.assertIn(w12, tag_one)
        self.assertIn(w13, tag_one)
        self.assertIn(w11, tag_another)
        self.assertIn(w12, tag_another)

    # - Find tags in a workitem
    def test_find_tags(self):
        user = self.data['user@local.host']
        w11 = self._add_workitem('#one #1 # ###десять #_TAG #one| #1', 'w11')
        tags = w11.get_tags()
        self.assertEqual(len(tags), 4)
        self.assertIn('one', tags)
        self.assertIn('1', tags)
        self.assertIn('десять', tags)
        self.assertIn('_tag', tags)

        w12 = self._add_workitem('', 'w12')
        tags = w12.get_tags()
        self.assertEqual(len(tags), 0)

    # - Get tags for different users
    def test_different_users(self):
        user = self.data['user@local.host']
        w11_local = self._add_workitem('#local_tag', 'w11')

        self.source.execute_prepared_strategy(CreateUserStrategy(
            11,
            datetime.datetime.now(datetime.timezone.utc),
            'admin@local.host',
            ['alice', 'Alice'],
            self.settings,
            None), False, True)

        self.source.execute_prepared_strategy(CreateUserStrategy(
            12,
            datetime.datetime.now(datetime.timezone.utc),
            'admin@local.host',
            ['bob', 'Bob'],
            self.settings,
            None), False, True)

        self.source.execute_prepared_strategy(CreateBacklogStrategy(
            13,
            datetime.datetime.now(datetime.timezone.utc),
            'alice',
            ['b1', 'First backlog'],
            self.settings,
            None), False, True)

        self.source.execute_prepared_strategy(CreateBacklogStrategy(
            14,
            datetime.datetime.now(datetime.timezone.utc),
            'bob',
            ['b1', 'First backlog'],
            self.settings,
            None), False, True)

        self.source.execute_prepared_strategy(CreateWorkitemStrategy(
            15,
            datetime.datetime.now(datetime.timezone.utc),
            'alice',
            ['w11', 'b1', '#alice_tag'],
            self.settings,
            None), False, True)

        self.source.execute_prepared_strategy(CreateWorkitemStrategy(
            16,
            datetime.datetime.now(datetime.timezone.utc),
            'bob',
            ['w11', 'b1', '#bob_tag'],
            self.settings,
            None), False, True)


        local_tags = self.data['user@local.host'].get_tags()
        self.assertEqual(len(local_tags), 1)
        self.assertIn('local_tag', local_tags)

        alice_tags = self.data['alice'].get_tags()
        self.assertEqual(len(alice_tags), 1)
        self.assertIn('alice_tag', alice_tags)

        bob_tags = self.data['bob'].get_tags()
        self.assertEqual(len(bob_tags), 1)
        self.assertIn('bob_tag', bob_tags)


    # - Check if FileEventSource loads tags correctly
    def test_file_event_source(self):
        settings = MockSettings(filename='src/fk/tests/fixtures/test-tags.txt')
        source = FileEventSource[Tenant](settings,
                                         FernetCryptograph(settings),
                                         Tenant(settings))
        source.start()
        data = source.get_data()
        self.assertIn('alice@flowkeeper.org', data)

        tags = data['alice@flowkeeper.org'].get_tags()
        self.assertEqual(len(tags), 5)
        self.assertIn('one', tags)
        self.assertIn('1', tags)
        self.assertIn('десять', tags)
        self.assertIn('_tag', tags)
        self.assertIn('two', tags)

        source.execute_prepared_strategy(CreateWorkitemStrategy(
            5,
            datetime.datetime.now(datetime.timezone.utc),
            'alice@flowkeeper.org',
            ['w13', '123-456-789', 'Tags #three and #four'],
            self.settings,
            None), False, False)
        self.assertEqual(len(tags), 7)
        self.assertIn('three', tags)
        self.assertIn('four', tags)

    # - Tags class
    def test_tags_class(self):
        w = self._add_workitem('There is #one tag', 'w11')
        user = self.data['user@local.host']

        tags = user.get_tags()
        self.assertEqual(type(tags), Tags)
        self.assertEqual(tags.get_parent(), user)

        tag = tags['one']
        self.assertEqual(type(tag), Tag)
        self.assertEqual(tag.get_parent(), tags)

    # - Events: TagDeleted
    def test_tag_deleted_event(self):
        fired = list()

        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'TagDeleted':
                self.assertIn('tag', kwargs)
                tag = kwargs['tag']
                self.assertEqual(tag.get_uid(), 'deleted')
                self.assertEqual(tag.get_parent().get_parent(), self.data['user@local.host'])
            elif event == 'TagContentChanged':
                self.assertIn('tag', kwargs)
                tag = kwargs['tag']
                self.assertEqual(tag.get_uid(), 'deleted')
                self.assertEqual(len(tag.get_workitems()), 0)

        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', 'Tags #one, #two and #deleted'])

        self.source.on('*', on_event)
        self.source.execute(RenameWorkitemStrategy, ['w11', 'Tags #one and #two only'])

        self.assertEqual(len(fired), 6)
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeWorkitemRename')
        self.assertEqual(fired[2], 'TagContentChanged')
        self.assertEqual(fired[3], 'TagDeleted')
        self.assertEqual(fired[4], 'AfterWorkitemRename')
        self.assertEqual(fired[5], 'AfterMessageProcessed')

    # - Events: TagContentChanged
    def test_tag_content_changed_event(self):
        fired = list()

        def on_event(event, **kwargs):
            fired.append(event)
            if event == 'TagContentChanged':
                self.assertIn('tag', kwargs)
                tag = kwargs['tag']
                self.assertEqual(tag.get_uid(), 'new')
                self.assertEqual(len(tag.get_workitems()), 2)

        self._standard_backlog()
        self.source.execute(CreateWorkitemStrategy, ['w11', 'b1', '#New workitem'])

        self.source.on('*', on_event)
        self.source.execute(CreateWorkitemStrategy, ['w12', 'b1', 'Another #new workitem'])

        self.assertEqual(len(fired), 5)
        self.assertEqual(fired[0], 'BeforeMessageProcessed')
        self.assertEqual(fired[1], 'BeforeWorkitemCreate')
        self.assertEqual(fired[2], 'TagContentChanged')
        self.assertEqual(fired[3], 'AfterWorkitemCreate')
        self.assertEqual(fired[4], 'AfterMessageProcessed')

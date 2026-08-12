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
from unittest import TestCase

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings, S
from fk.core.ephemeral_event_source import EphemeralEventSource
from fk.core.fernet_cryptograph import FernetCryptograph
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User


class TestSettings(TestCase):
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

    def test_defaults(self):
        val1 = self.settings.get(S.POMODORO_DEFAULT_WORK_DURATION)
        self.assertEqual(val1, str(25 * 60))
        val2 = self.settings.get(S.APPLICATION_TIMER_UI_MODE)
        self.assertEqual(val2, 'focus')

    def test_invalid_setting(self):
        self.assertRaises(Exception,
                          lambda: self.settings.get('Invalid.name'))

    def test_categories(self):
        categories = self.settings.get_categories()
        self.assertEqual(len(categories), 7)
        self.assertIn('General', categories)
        self.settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: '10',
        })
        general = self.settings.get_settings('General')
        found = False
        for s in general:
            if s[0] == S.POMODORO_DEFAULT_WORK_DURATION:
                found = True
                self.assertEqual(s[1], 'duration')
                self.assertEqual(s[3], '10')
        self.assertTrue(found)

    def test_get_set(self):
        self.settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: '11',
        })
        self.assertEqual(self.settings.get(S.POMODORO_DEFAULT_WORK_DURATION), '11')

    def test_clear(self):
        # What's the difference between this and reset_to_defaults()?
        self.settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: '12',
        })
        self.settings.clear()
        self.assertEqual(self.settings.get(S.POMODORO_DEFAULT_WORK_DURATION), str(25 * 60))

    def test_reset(self):
        self.settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: '13',
        })
        self.settings.reset_to_defaults()
        self.assertEqual(self.settings.get(S.POMODORO_DEFAULT_WORK_DURATION), str(25 * 60))

    def test_location(self):
        self.assertEqual(self.settings.location(), 'N/A')

    def test_shortcuts(self):
        self.settings.set({
            S.SOURCE_TYPE: 'local',
            S.POMODORO_DEFAULT_WORK_DURATION: '14',
            S.POMODORO_DEFAULT_REST_DURATION: '15',
            S.SOURCE_FULLNAME: 'John Doe',
        })
        self.assertEqual(self.settings.get_username(), 'user@local.host')
        self.assertEqual(self.settings.get_work_duration(), 14)
        self.assertEqual(self.settings.get_rest_duration(), 15)
        self.assertEqual(self.settings.get_fullname(), 'John Doe')
        self.assertFalse(self.settings.is_team_supported(), False)
        self.settings.set({
            S.SOURCE_TYPE: 'flowkeeper.org',
            S.WEBSOCKETEVENTSOURCE_USERNAME: 'alice@example.org',
            S.APPLICATION_ENABLE_TEAMS: 'True',
        })
        self.assertEqual(self.settings.get_username(), 'alice@example.org')
        self.assertTrue(self.settings.is_team_supported())

    def test_visibility(self):
        self.settings.reset_to_defaults()
        visible = self.settings.get_displayed_settings()
        # Always
        self.assertIn(S.SOURCE_TYPE, visible)
        self.assertIn(S.APPLICATION_EYECANDY_TYPE, visible)
        self.assertIn(S.POMODORO_DEFAULT_WORK_DURATION, visible)
        self.assertIn(S.APPLICATION_PLAY_TICK_SOUND, visible)
        # Never
        self.assertNotIn(S.APPLICATION_WINDOW_WIDTH, visible)
        self.assertNotIn(S.APPLICATION_SHOW_STATUS_BAR, visible)
        self.assertNotIn(S.WEBSOCKETEVENTSOURCE_REFRESH_TOKEN, visible)
        self.assertNotIn(S.SOURCE_FULLNAME, visible)
        self.assertNotIn(S.APPLICATION_HIDE_COMPLETED, visible)
        # For file event source
        self.assertIn(S.FILEEVENTSOURCE_FILENAME, visible)
        self.assertNotIn(S.WEBSOCKETEVENTSOURCE_AUTH_TYPE, visible)
        self.assertNotIn(S.WEBSOCKETEVENTSOURCE_URL, visible)
        # For Flowkeeper.org event source
        self.settings.set({
            S.SOURCE_TYPE: 'flowkeeper.org',
        })
        visible = self.settings.get_displayed_settings()
        self.assertNotIn(S.FILEEVENTSOURCE_FILENAME, visible)
        self.assertIn(S.WEBSOCKETEVENTSOURCE_AUTH_TYPE, visible)
        self.assertNotIn(S.WEBSOCKETEVENTSOURCE_USERNAME, visible)
        self.assertNotIn(S.WEBSOCKETEVENTSOURCE_URL, visible)
        # For custom WS event source
        self.settings.set({
            S.SOURCE_TYPE: 'websocket',
            S.WEBSOCKETEVENTSOURCE_AUTH_TYPE: 'basic',
        })
        visible = self.settings.get_displayed_settings()
        self.assertIn(S.WEBSOCKETEVENTSOURCE_USERNAME, visible)
        self.assertIn(S.WEBSOCKETEVENTSOURCE_URL, visible)

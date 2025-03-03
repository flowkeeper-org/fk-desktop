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
from fk.core.abstract_settings import AbstractSettings
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
        val1 = self.settings.get('Pomodoro.default_work_duration')
        self.assertEqual(val1, str(25 * 60))
        val2 = self.settings.get('Application.timer_ui_mode')
        self.assertEqual(val2, 'focus')

    def test_invalid_setting(self):
        self.assertRaises(Exception,
                          lambda: self.settings.get('Invalid.name'))

    def test_categories(self):
        categories = self.settings.get_categories()
        self.assertEqual(len(categories), 7)
        self.assertIn('General', categories)
        self.settings.set({
            'Pomodoro.default_work_duration': '10',
        })
        general = self.settings.get_settings('General')
        found = False
        for s in general:
            if s[0] == 'Pomodoro.default_work_duration':
                found = True
                self.assertEqual(s[1], 'duration')
                self.assertEqual(s[3], '10')
        self.assertTrue(found)

    def test_get_set(self):
        self.settings.set({
            'Pomodoro.default_work_duration': '11',
        })
        self.assertEqual(self.settings.get('Pomodoro.default_work_duration'), '11')

    def test_clear(self):
        # What's the difference between this and reset_to_defaults()?
        self.settings.set({
            'Pomodoro.default_work_duration': '12',
        })
        self.settings.clear()
        self.assertEqual(self.settings.get('Pomodoro.default_work_duration'), str(25 * 60))

    def test_reset(self):
        self.settings.set({
            'Pomodoro.default_work_duration': '13',
        })
        self.settings.reset_to_defaults()
        self.assertEqual(self.settings.get('Pomodoro.default_work_duration'), str(25 * 60))

    def test_location(self):
        self.assertEqual(self.settings.location(), 'N/A')

    def test_shortcuts(self):
        self.settings.set({
            'Source.type': 'local',
            'Pomodoro.default_work_duration': '14',
            'Pomodoro.default_rest_duration': '15',
            'Source.fullname': 'John Doe',
        })
        self.assertEqual(self.settings.get_username(), 'user@local.host')
        self.assertEqual(self.settings.get_work_duration(), 14)
        self.assertEqual(self.settings.get_rest_duration(), 15)
        self.assertEqual(self.settings.get_fullname(), 'John Doe')
        self.assertFalse(self.settings.is_team_supported(), False)
        self.settings.set({
            'Source.type': 'flowkeeper.org',
            'WebsocketEventSource.username': 'alice@example.org',
            'Application.enable_teams': 'True',
        })
        self.assertEqual(self.settings.get_username(), 'alice@example.org')
        self.assertTrue(self.settings.is_team_supported())

    def test_visibility(self):
        self.settings.reset_to_defaults()
        visible = self.settings.get_displayed_settings()
        # Always
        self.assertIn('Source.type', visible)
        self.assertIn('Application.eyecandy_type', visible)
        self.assertIn('Pomodoro.default_work_duration', visible)
        self.assertIn('Application.play_tick_sound', visible)
        # Never
        self.assertNotIn('Application.window_width', visible)
        self.assertNotIn('Application.show_status_bar', visible)
        self.assertNotIn('WebsocketEventSource.refresh_token!', visible)
        self.assertNotIn('Source.fullname', visible)
        self.assertNotIn('Application.hide_completed', visible)
        # For file event source
        self.assertIn('FileEventSource.filename', visible)
        self.assertNotIn('WebsocketEventSource.auth_type', visible)
        self.assertNotIn('WebsocketEventSource.url', visible)
        # For Flowkeeper.org event source
        self.settings.set({
            'Source.type': 'flowkeeper.org',
        })
        visible = self.settings.get_displayed_settings()
        self.assertNotIn('FileEventSource.filename', visible)
        self.assertIn('WebsocketEventSource.auth_type', visible)
        self.assertNotIn('WebsocketEventSource.username', visible)
        self.assertNotIn('WebsocketEventSource.url', visible)
        # For custom WS event source
        self.settings.set({
            'Source.type': 'websocket',
            'WebsocketEventSource.auth_type': 'basic',
        })
        visible = self.settings.get_displayed_settings()
        self.assertIn('WebsocketEventSource.username', visible)
        self.assertIn('WebsocketEventSource.url', visible)

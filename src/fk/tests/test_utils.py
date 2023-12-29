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

from fk.core.abstract_settings import AbstractSettings
from fk.core.app import App
from fk.core.mock_settings import MockSettings
from fk.core.user import User

PREDEFINED_TIMESTAMP = [1632408308, 1666626369, 1700938030]
PREDEFINED_UID = ['a00001', 'a00002', 'a00003', 'a00004', 'a00005']
TEST_USERNAMES = ['alice@flowkeeper.org', 'bob@flowkeeper.org', 'charlie@flowkeeper.org']


def check_timestamp(t: datetime.datetime, n: int) -> bool:
    return int(t.timestamp()) == PREDEFINED_TIMESTAMP[n]


def predefined_datetime(n: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(PREDEFINED_TIMESTAMP[n], tz=datetime.timezone.utc)


def predefined_uid(n: int) -> str:
    return PREDEFINED_UID[n]


def noop_emit(event: str, params: dict[str, any]) -> None:
    pass
    # print('Emit trace', event, params)


def test_user(n: int) -> User:
    return User(
        None,
        TEST_USERNAMES[n],
        f'Test User #{n}',
        predefined_datetime(0),
        False)


def test_users() -> dict[str, User]:
    return {
        TEST_USERNAMES[0]: test_user(0),
        TEST_USERNAMES[1]: test_user(1),
        TEST_USERNAMES[2]: test_user(2),
    }


def test_settings(n: int) -> AbstractSettings:
    return MockSettings(username=TEST_USERNAMES[n])


def test_data() -> App:
    app = App(test_settings(0))
    users = test_users()
    for u in users:
        app[u] = users[u]
    return app

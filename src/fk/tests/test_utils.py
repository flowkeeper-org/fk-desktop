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
from __future__ import annotations

import datetime
import math
import secrets
import sys
from typing import TypeVar

from fk.core.abstract_settings import AbstractSettings
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.core.user import User

PREDEFINED_TIMESTAMP = [1632408308, 1666626369, 1700938030]
PREDEFINED_UID = ['a00001', 'a00002', 'a00003', 'a00004', 'a00005']
TEST_USERNAMES = ['alice@flowkeeper.org', 'bob@flowkeeper.org', 'charlie@flowkeeper.org']
_T = TypeVar('_T')


def check_timestamp(t: datetime.datetime, n: int) -> bool:
    return int(t.timestamp()) == PREDEFINED_TIMESTAMP[n]


def predefined_datetime(n: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(PREDEFINED_TIMESTAMP[n], tz=datetime.timezone.utc)


def predefined_uid(n: int) -> str:
    return PREDEFINED_UID[n]


def noop_emit(event: str, params: dict[str, any], carry: any) -> None:
    pass


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


def test_data() -> Tenant:
    tenant = Tenant(test_settings(0))
    users = test_users()
    for u in users:
        tenant[u] = users[u]
    return tenant


##########################################################################################
# Random stuff
##########################################################################################
def one_of(seq: list[_T]) -> _T:
    return secrets.choice(seq)


def randint(a: int, b: int) -> int:
    return a + secrets.randbelow(b + 1)


def random() -> float:
    # This is slow, but works correctly
    return secrets.randbits(int(8 * math.log(sys.maxsize, 256))) / sys.maxsize


# Good enough normally distributed random number
def rand_normal(a: int, b: int) -> int:
    return round(sum([randint(a, b) for x in range(5)]) / 5)


def shuffle(seq: list[_T]) -> list[_T]:
    res = list()
    lst = list(seq)
    while len(lst) > 0:
        v = one_of(lst)
        res.append(v)
        lst.remove(v)
    return res

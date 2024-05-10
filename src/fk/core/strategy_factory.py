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
import re
from typing import Callable, Type, TypeVar

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.user import User

REGEX = re.compile(r'([1-9][0-9]*)\s*,\s*'
                   r'([0-9: .\-+]+)\s*,\s*'
                   r'([\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4})\s*:\s*'
                   r'([a-zA-Z]+)\s*\(\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)?"\s*(?:,\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)")?\s*(?:,\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)"\s*)*\)')

STRATEGY_CLASS_NAME_REGEX = re.compile(r'([A-Z][a-zA-Z]*)Strategy')

STRATEGIES = dict()

TRoot = TypeVar('TRoot')


def strategy(cls: Type[AbstractStrategy[TRoot]]):
    m = STRATEGY_CLASS_NAME_REGEX.search(cls.__name__)
    if m is not None:
        name = m.group(1)
        # print(f'Registering strategy {name} -> {cls.__name__}')
        STRATEGIES[name] = cls
        return cls
    else:
        raise Exception(f"Invalid strategy class name: {cls.__name__}")


def strategy_seq_from_string(s: str) -> int | None:
    # Empty strings and comments are special cases
    if s.strip() == '' or s.startswith('#'):
        return None

    m = REGEX.search(s)
    if m is not None:
        return int(m.group(1))


def strategy_from_string(s: str,
                         emit: Callable[[str, dict[str, any], any], None],
                         data: TRoot,
                         settings: AbstractSettings,
                         cryptograph: AbstractCryptograph,
                         replacement_user: User | None = None) -> AbstractStrategy[TRoot] | str:
    # Empty strings and comments are special cases
    if s.strip() == '' or s.startswith('#'):
        return s

    m = REGEX.search(s)
    if m is not None:
        name = m.group(4)
        if name not in STRATEGIES:
            raise Exception(f"Unknown strategy: {name}")

        seq = int(m.group(1))
        when = datetime.datetime.fromisoformat(m.group(2))
        who = m.group(3)
        user = replacement_user if replacement_user is not None else data.get_user(who)
        params = list(filter(lambda p: p is not None, m.groups()[4:]))
        params = [p.replace('\\"', '"').replace('\\\\', '\\') for p in params]

        # TODO: Enable trace
        # print (f"Initializing: '{seq}' / '{when}' / '{user}' / '{name}' / {params}")
        return STRATEGIES[name](seq, when, user, params, emit, data, settings, cryptograph)
    else:
        raise Exception(f"Bad syntax: {s}")

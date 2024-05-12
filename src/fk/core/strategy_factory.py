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

import re
from typing import Type, TypeVar

from fk.core.abstract_strategy import AbstractStrategy

STRATEGY_CLASS_NAME_REGEX = re.compile(r'([A-Z][a-zA-Z]*)Strategy')
TRoot = TypeVar('TRoot')
STRATEGIES = dict[str, Type[AbstractStrategy[TRoot]]]()


def strategy(cls: Type[AbstractStrategy[TRoot]]):
    m = STRATEGY_CLASS_NAME_REGEX.search(cls.__name__)
    if m is not None:
        name = m.group(1)
        # print(f'Registering strategy {name} -> {cls.__name__}')
        STRATEGIES[name] = cls
        return cls
    else:
        raise Exception(f"Invalid strategy class name: {cls.__name__}")

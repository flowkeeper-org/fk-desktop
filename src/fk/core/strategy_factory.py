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
from typing import Callable

from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import (CreateBacklogStrategy,
                                        RenameBacklogStrategy,
                                        DeleteBacklogStrategy)
from fk.core.pomodoro_strategies import (AddPomodoroStrategy,
                                         RemovePomodoroStrategy,
                                         StartWorkStrategy,
                                         StartRestStrategy,
                                         CompletePomodoroStrategy)
from fk.core.user import User
from fk.core.user_strategies import (CreateUserStrategy,
                                     RenameUserStrategy,
                                     DeleteUserStrategy)
from fk.core.workitem_strategies import (CreateWorkitemStrategy,
                                         RenameWorkitemStrategy,
                                         CompleteWorkitemStrategy,
                                         DeleteWorkitemStrategy)

REGEX = re.compile(r'([1-9][0-9]*)\s*,\s*'
                   r'([0-9: .\-+]+)\s*,\s*'
                   r'([\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4})\s*:\s*'
                   r'([a-zA-Z]+)\s*\(\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)?"\s*(?:,\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)")?\s*(?:,\s*'
                   r'"((?:[^"\\]|\\"|\\\\)*)"\s*)*\)')


def strategy_from_string(s: str,
                         emit: Callable[[str, dict[str, any]], None],
                         data: dict[str, User],
                         settings: AbstractSettings) -> AbstractStrategy | str:
    # Empty strings and comments are special cases
    if s.strip() == '' or s.startswith('#'):
        return s

    m = REGEX.search(s)
    if m is not None:
        seq = int(m.group(1))
        when = datetime.datetime.fromisoformat(m.group(2))
        who = m.group(3)
        name = m.group(4)
        params = list(filter(lambda p: p is not None, m.groups()[4:]))
        params = [p.replace('\\"', '"').replace('\\\\', '\\') for p in params]

        # TODO: Enable trace
        # TODO: We are not handling 0 or 1 parameters correctly
        # print (f"Initializing: '{seq}' / '{when}' / '{who}' / '{name}' / {params}")

        if name == 'CreateUser':
            class_name = CreateUserStrategy
        elif name == 'DeleteUser':
            class_name = DeleteUserStrategy
        elif name == 'RenameUser':
            class_name = RenameUserStrategy
        elif name == 'CreateBacklog':
            class_name = CreateBacklogStrategy
        elif name == 'CreateWorkitem':
            class_name = CreateWorkitemStrategy
        elif name == 'RenameBacklog':
            class_name = RenameBacklogStrategy
        elif name == 'CompleteWorkitem':
            class_name = CompleteWorkitemStrategy
        elif name == 'AddPomodoro':
            class_name = AddPomodoroStrategy
        elif name == 'RemovePomodoro':
            class_name = RemovePomodoroStrategy
        elif name == 'CompletePomodoro':
            class_name = CompletePomodoroStrategy
        elif name == 'StartWork':
            class_name = StartWorkStrategy
        elif name == 'StartRest':
            class_name = StartRestStrategy
        elif name == 'DeleteBacklog':
            class_name = DeleteBacklogStrategy
        elif name == 'DeleteWorkitem':
            class_name = DeleteWorkitemStrategy
        elif name == 'RenameWorkitem':
            class_name = RenameWorkitemStrategy
        else:
            raise Exception(f"Unknown strategy: {name}")

        return class_name(seq, when, who, params, emit, data, settings)
    else:
        raise Exception(f"Bad syntax: {s}")

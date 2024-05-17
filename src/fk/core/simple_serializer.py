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
from datetime import datetime
from typing import TypeVar

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.strategy_factory import STRATEGIES

TRoot = TypeVar('TRoot')


class SimpleSerializer(AbstractSerializer[str, TRoot]):
    REGEX = re.compile(r'([1-9][0-9]*)\s*,\s*'
                       r'([0-9: .\-+]+)\s*,\s*'
                       r'([\w\-.]+@(?:[\w-]+\.)+[\w-]{2,4})\s*:\s*'
                       r'([a-zA-Z]+)\s*\(\s*'
                       r'"((?:[^"\\]|\\"|\\\\)*)?"\s*(?:,\s*'
                       r'"((?:[^"\\]|\\"|\\\\)*)")?\s*(?:,\s*'
                       r'"((?:[^"\\]|\\"|\\\\)*)"\s*)*\)')

    def __init__(self, settings: AbstractSettings, cryptograph: AbstractCryptograph):
        print(f'SimpleSerializer.__init__({settings}, {cryptograph})')
        super().__init__(settings, cryptograph)

    @staticmethod
    def escape_parameter(value):
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def serialize(self, s: AbstractStrategy) -> str:
        # Escape params
        escaped = [SimpleSerializer.escape_parameter(p) for p in s.get_params()]
        if len(escaped) < 2:
            escaped.append("")
        if len(escaped) < 2:
            escaped.append("")
        params = '"' + '", "'.join(escaped) + '"'
        plaintext = f'{s.get_sequence()}, {s.get_when()}, {s.get_user_identity()}: {s.get_name()}({params})'
        if self._cryptograph.enabled and s.encryptable():
            return '+' + self._cryptograph.encrypt(plaintext)
        else:
            return plaintext

    def deserialize(self, t: str) -> AbstractStrategy[TRoot] | None:
        if t.startswith('+'):
            plaintext = self._cryptograph.decrypt(t[1:])
        else:
            plaintext = t

        # Empty strings and comments are special cases
        if plaintext.strip() == '' or plaintext.startswith('#'):
            return None

        m = self.REGEX.search(plaintext)
        if m is not None:
            name = m.group(4)
            if name not in STRATEGIES:
                raise Exception(f"Unknown strategy: {name}")

            seq = int(m.group(1))
            when = datetime.fromisoformat(m.group(2))
            user = m.group(3)
            params = list(filter(lambda p: p is not None, m.groups()[4:]))
            params = [p.replace('\\"', '"').replace('\\\\', '\\') for p in params]

            # TODO: Enable trace
            # print (f"Initializing: '{seq}' / '{when}' / '{user}' / '{name}' / {params}")
            return STRATEGIES[name](seq, when, user, params, self._settings, self._cryptograph)
        else:
            raise Exception(f"Bad syntax: {plaintext}")

    def __str__(self):
        return f'SimpleSerializer with settings {self._settings} and cryptograph {self._cryptograph}'
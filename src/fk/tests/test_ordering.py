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
from itertools import permutations
from statistics import mean

from fk.core.backlog import Backlog
from fk.core.ordering import get_reordering_strategies
from fk.core.tenant import Tenant, ADMIN_USER
from fk.core.user import User
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import ReorderWorkitemStrategy
from fk.tests.abstract_test_case import AbstractTestCase


def _nothing(*args, **kwargs):
    pass


def _keys(lst: list[Workitem]):
    return ', '.join([w.get_uid() for w in lst])


class TestEvents(AbstractTestCase):
    backlog: Backlog
    tenant: Tenant

    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)
        self.tenant: Tenant = Tenant(None)
        user: User = self.tenant[ADMIN_USER]
        self.backlog = Backlog('Backlog', user, 'b-1', datetime.datetime.now(tz=datetime.timezone.utc))
        user['b-1'] = self.backlog

    def _create_workitem(self, i) -> Workitem:
        w = Workitem(f'Workitem {i}', f'w-{i}', self.backlog, datetime.datetime.now(tz=datetime.timezone.utc), set())
        self.backlog[f'w-{i}'] = w
        return w

    def _internal_test(self, src: list[Workitem], trg: list[Workitem]) -> int:
        strategies = [
            ReorderWorkitemStrategy(0,
                                    datetime.datetime.now(tz=datetime.timezone.utc),
                                    ADMIN_USER,
                                    params,
                                    None)
            for params in get_reordering_strategies(src, trg)
        ]

        for s in strategies:
            s.execute(_nothing, self.tenant)

        msg = f'{_keys(src) != list(self.backlog.keys())}'
        for i, w in enumerate(self.backlog.values()):
            self.assertEqual(w.get_uid(), trg[i].get_uid(), msg)

        return len(strategies)

    def _internal_full_test(self, size: int):
        trg = [self._create_workitem(i) for i in range(size)]
        avg = mean([
            self._internal_test(list(src), trg)
            for src in permutations(trg)
        ])
        return avg

    def test_1(self):
        avg = self._internal_full_test(1)
        self.assertEqual(avg, 0)

    def test_2(self):
        avg = self._internal_full_test(2)
        self.assertEqual(avg, 0.5)

    def test_3(self):
        avg = self._internal_full_test(3)
        self.assertEqual(avg, 1)

    def test_4(self):
        avg = self._internal_full_test(4)
        self.assertEqual(avg, 1.5)

    def test_5(self):
        avg = self._internal_full_test(5)
        self.assertEqual(avg, 2.091666666666667)

    def test_6(self):
        avg = self._internal_full_test(6)
        self.assertEqual(avg, 2.6958333333333333)


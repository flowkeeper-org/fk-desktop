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
import random
import sys
from typing import Iterable

from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import CreateBacklogStrategy
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro_strategies import AddPomodoroStrategy, StartWorkStrategy, VoidPomodoroStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tenant import ADMIN_USER
from fk.core.user_strategies import CreateUserStrategy
from fk.core.workitem_strategies import CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.tests.test_utils import one_of, shuffle, randint, rand_normal

PROJECTS = ['#Alpha', '#Beta', '#Gamma', '#Delta', '#Omega']

VERBS = ['Create', 'Generate', 'Fix', 'Explore', 'Request',
         'Send', 'Document', 'Think about', 'Plan', 'Draw',
         'Deprecate', 'Explain', 'Check', 'Verify', 'Find']

NOUNS = ['screenshot', 'bug', 'code', 'function', 'website',
         'documentation', 'script', 'tool', 'email', 'new feature',
         'automation', 'scheme', 'design', 'architecture', 'idea']


def lorem_ipsum() -> str:
    return f'{one_of(VERBS)} {one_of(NOUNS)} for {one_of(PROJECTS)}'


def emulate(days: int, user: str) -> Iterable[AbstractStrategy]:
    seq = 1
    day = days + 1
    while day > 0:
        day -= 1
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=day)
        if now.weekday() >= 5:
            continue

        now = datetime.datetime(now.year, now.month, now.day,
                                rand_normal(8, 10), randint(0, 59),
                                tzinfo=datetime.timezone.utc)

        if seq == 1:
            yield CreateUserStrategy(seq,
                                     now,
                                     ADMIN_USER,
                                     [user, user],
                                     settings)

        seq += 1
        now += datetime.timedelta(seconds=rand_normal(1, 60))
        backlog_uid = generate_uid()
        backlog_name = now.strftime('%Y-%m-%d, %A')
        yield CreateBacklogStrategy(seq,
                                    now,
                                    user,
                                    [backlog_uid, backlog_name],
                                    settings)

        pomodoros = list[str]()
        for w in range(rand_normal(1, 10)):
            seq += 1
            now += datetime.timedelta(seconds=rand_normal(1, 60))
            workitem_uid = generate_uid()
            yield CreateWorkitemStrategy(seq,
                                         now,
                                         user,
                                         [workitem_uid, backlog_uid, lorem_ipsum()],
                                         settings)

            for p in range(rand_normal(0, 4)):
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 10))
                pomodoros.append(workitem_uid)
                yield AddPomodoroStrategy(seq,
                                          now,
                                          user,
                                          [workitem_uid, '1'],
                                          settings)

        shuffle(pomodoros)
        for p in pomodoros:
            choice = randint(1, 10)
            if choice < 3:  # Ignore it
                continue
            else:
                # Start it and...
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 120))
                yield StartWorkStrategy(seq,
                                        now,
                                        user,
                                        [p, '1500', '300'],
                                        settings)

                if choice < 5:  # Void it
                    seq += 1
                    now += datetime.timedelta(seconds=rand_normal(1, 1800))
                    yield VoidPomodoroStrategy(seq,
                                               now,
                                               user,
                                               [p, 'Voided for a good reason' if random.random() < 0.5 else ''],
                                               settings)
                else:   # Complete it -- just increment the timer, let it "finish"
                    now += datetime.timedelta(seconds=1800)

                if choice > 8:
                    seq += 1
                    now += datetime.timedelta(seconds=rand_normal(1, 10))
                    yield AddPomodoroStrategy(seq,
                                              now,
                                              user,
                                              [p, '1'],
                                              settings)

        for w in set(pomodoros):
            choice = randint(1, 10)
            if choice < 4:  # Ignore it
                continue
            else:   # Complete it
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 120))
                yield CompleteWorkitemStrategy(seq,
                                               now,
                                               user,
                                               [w, 'finished'],
                                               settings)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: PYTHONPATH=src python -m fk.tests.data_generator <DAYS>')
        print('Where DAYS is the number of days to emulate. The results are output to STDOUT.')
        exit(1)

    settings = MockSettings()
    serializer = SimpleSerializer(settings, NoCryptograph(settings))
    for strategy in emulate(int(sys.argv[1]), 'user@local.host'):
        print(serializer.serialize(strategy))

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
import sys
from typing import Iterable

from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import CreateBacklogStrategy, RenameBacklogStrategy, DeleteBacklogStrategy
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro_strategies import AddPomodoroStrategy, AddInterruptionStrategy, RemovePomodoroStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tenant import ADMIN_USER
from fk.core.timer_strategies import StopTimerStrategy, StartTimerStrategy
from fk.core.user_strategies import CreateUserStrategy
from fk.core.workitem_strategies import CreateWorkitemStrategy, CompleteWorkitemStrategy, DeleteWorkitemStrategy, \
    RenameWorkitemStrategy
from fk.tests.test_utils import one_of, shuffle, randint, rand_normal, random

PROJECTS = ['#Alpha', '#Beta', '#Gamma', '#Delta', '#Omega']

VERBS = ['Create', 'Generate', 'Fix', 'Explore', 'Request',
         'Send', 'Document', 'Think about', 'Plan', 'Draw',
         'Deprecate', 'Explain', 'Check', 'Verify', 'Find']

NOUNS = ['screenshot', 'bug', 'code', 'function', 'website',
         'documentation', 'script', 'tool', 'email', 'new feature',
         'automation', 'scheme', 'design', 'architecture', 'idea']


def lorem_ipsum() -> str:
    return f'{one_of(VERBS)} {one_of(NOUNS)} for {one_of(PROJECTS)}'


def lorem_ipsum_backlog() -> str:
    return f'Template for {one_of(PROJECTS)}'


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

        pomodoros = list[tuple[str, str]]()
        incomplete_workitems = set[str]()

        for w in range(rand_normal(1, 10)):
            seq += 1
            now += datetime.timedelta(seconds=rand_normal(1, 60))
            workitem_uid = generate_uid()
            yield CreateWorkitemStrategy(seq,
                                         now,
                                         user,
                                         [workitem_uid, backlog_uid, lorem_ipsum()],
                                         settings)
            incomplete_workitems.add(workitem_uid)

            if randint(0, 10) > 6:
                # This *will be* a tracker pomodoro. AddPomodoro will be called later.
                for _ in range(rand_normal(0, 8)):
                    pomodoros.append((workitem_uid, 'tracker'))
            else:
                # Normal pomodoro
                for _ in range(rand_normal(0, 4)):
                    seq += 1
                    now += datetime.timedelta(seconds=rand_normal(1, 10))
                    pomodoros.append((workitem_uid, 'normal'))
                    yield AddPomodoroStrategy(seq,
                                              now,
                                              user,
                                              [workitem_uid, '1', 'normal'],
                                              settings)

        completed_in_series = 0
        shuffle(pomodoros)

        while len(pomodoros) > 0:
            workitem_uid, pomodoro_type = pomodoros.pop()

            choice = randint(1, 10)
            if choice < 2:
                continue    # Ignore it
            elif choice < 3 and pomodoro_type == 'normal':
                # Remove it
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 60))
                yield RemovePomodoroStrategy(seq,
                                             now,
                                             user,
                                             [workitem_uid, '1'],
                                             settings)
                continue

            if random() < 0.2:
                # Rename workitem
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 60))
                yield RenameWorkitemStrategy(seq,
                                             now,
                                             user,
                                             [workitem_uid, lorem_ipsum()],
                                             settings)

            if random() < 0.01:
                # Rename backlog
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 60))
                yield RenameBacklogStrategy(seq,
                                            now,
                                            user,
                                            [backlog_uid, lorem_ipsum_backlog()],
                                            settings)

            if random() < 0.01:
                # Delete backlog
                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 60))
                yield DeleteBacklogStrategy(seq,
                                            now,
                                            user,
                                            [backlog_uid],
                                            settings)
                incomplete_workitems.clear()
                break

            # Else, start it and...
            seq += 1
            now += datetime.timedelta(seconds=rand_normal(1, 120))

            if pomodoro_type == 'tracker':
                # That's what the GUI does for trackers -- it creates a pomodoro right before starting it
                yield AddPomodoroStrategy(seq,
                                          now,
                                          user,
                                          [workitem_uid, '1', 'tracker'],
                                          settings)
                seq += 1
                now += datetime.timedelta(seconds=0.01)
                yield StartTimerStrategy(seq,
                                         now,
                                         user,
                                         [workitem_uid],
                                         settings)

                seq += 1
                now += datetime.timedelta(seconds=rand_normal(1, 1200))
                if random() < 0.05:
                    yield CompleteWorkitemStrategy(seq,
                                                   now,
                                                   user,
                                                   [workitem_uid, 'finished'],
                                                   settings)
                    incomplete_workitems.remove(workitem_uid)
                    pomodoros = list(filter(lambda p: p[0] != workitem_uid, pomodoros))
                elif random() < 0.05:
                    yield DeleteWorkitemStrategy(seq,
                                                now,
                                                user,
                                                [workitem_uid],
                                                settings)
                    incomplete_workitems.remove(workitem_uid)
                    pomodoros = list(filter(lambda p: p[0] != workitem_uid, pomodoros))
                else:
                    yield StopTimerStrategy(seq,
                                            now,
                                            user,
                                            [],
                                            settings)
            else:
                # For normal pomodoros only
                yield StartTimerStrategy(seq,
                                         now,
                                         user,
                                         [workitem_uid, '1500', '300' if completed_in_series < 3 else '0'],
                                         settings)

                choice = randint(1, 10)
                if choice < 3:  # Void it
                    seq += 1
                    now += datetime.timedelta(seconds=rand_normal(1, 1800))
                    if random() < 0.5:
                        yield AddInterruptionStrategy(seq,
                                                      now,
                                                      user,
                                                      [workitem_uid, 'Voided for a good reason', ''],
                                                      settings)
                        seq += 1
                    yield StopTimerStrategy(seq,
                                            now,
                                            user,
                                            [],
                                            settings)
                else:
                    pomodoro_duration = 1500
                    if completed_in_series < 3:
                        pomodoro_duration += 300
                    else:
                        # Take a long break every 4 pomodoro
                        pomodoro_duration += randint(1, 3600)
                    if choice < 5:  # Add an interruption
                        seq += 1
                        after = rand_normal(1, pomodoro_duration)
                        now += datetime.timedelta(seconds=after)
                        yield AddInterruptionStrategy(seq,
                                                      now,
                                                      user,
                                                      [workitem_uid,
                                                       'An interruption' if random() < 0.5 else '',
                                                       str(after / 2) if random() < 0.5 else ''],
                                                      settings)

                    if random() < 0.05:
                        now += datetime.timedelta(seconds=randint(1, pomodoro_duration - 1))
                        seq += 1
                        yield CompleteWorkitemStrategy(seq,
                                                       now,
                                                       user,
                                                       [workitem_uid, 'finished'],
                                                       settings)
                        incomplete_workitems.remove(workitem_uid)
                        pomodoros = list(filter(lambda p: p[0] != workitem_uid, pomodoros))
                    elif random() < 0.05:
                        now += datetime.timedelta(seconds=randint(1, pomodoro_duration - 1))
                        seq += 1
                        yield DeleteWorkitemStrategy(seq,
                                                     now,
                                                     user,
                                                     [workitem_uid],
                                                     settings)
                        incomplete_workitems.remove(workitem_uid)
                        pomodoros = list(filter(lambda p: p[0] != workitem_uid, pomodoros))
                    else:
                        # Complete it -- just increment the timer, let it "finish"
                        now += datetime.timedelta(seconds=pomodoro_duration)
                        completed_in_series += 1
                        if completed_in_series == 4:
                            # We've just took a long break -- stop the timer and reset the series
                            seq += 1
                            yield StopTimerStrategy(seq,
                                                    now,
                                                    user,
                                                    [],
                                                    settings)
                            completed_in_series = 0

                        if choice > 8:
                            seq += 1
                            now += datetime.timedelta(seconds=rand_normal(1, 10))
                            yield AddPomodoroStrategy(seq,
                                                      now,
                                                      user,
                                                      [workitem_uid, '1', 'normal'],
                                                      settings)
                            pomodoros.append((workitem_uid, 'normal'))

        for w in incomplete_workitems:
            choice = randint(1, 10)
            if choice < 4:  # Ignore it
                continue

            # Else complete it
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

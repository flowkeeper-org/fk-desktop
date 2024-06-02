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
from os import path
from typing import Iterable, Callable, TypeVar

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, RenameBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro_strategies import AddPomodoroStrategy, VoidPomodoroStrategy, StartWorkStrategy, StartRestStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tenant import ADMIN_USER
from fk.core.user import User
from fk.core.user_strategies import CreateUserStrategy, RenameUserStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CreateWorkitemStrategy, CompleteWorkitemStrategy, RenameWorkitemStrategy

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


def _export_message_processed(source: AbstractEventSource[TRoot],
                              another: AbstractEventSource[TRoot],
                              export_file,
                              progress_callback: Callable[[int, int], None],
                              every: int,
                              strategy: AbstractStrategy[TRoot],
                              export_serializer: AbstractSerializer) -> None:
    serialized = export_serializer.serialize(strategy)
    export_file.write(f'{serialized}\n')
    if another._estimated_count % every == 0:
        progress_callback(another._estimated_count, source._estimated_count)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f' - {another._estimated_count} out of {source._estimated_count}')


def _export_completed(source: AbstractEventSource[TRoot],
                      another: AbstractEventSource[TRoot],
                      export_file,
                      completion_callback: Callable[[int], None]) -> None:
    export_file.close()
    completion_callback(another._estimated_count)


def compressed_strategies(source: AbstractEventSource[TRoot]) -> Iterable[AbstractStrategy]:
    """The minimal list of strategies required to get the same end result"""

    seq = 1
    for user in source.get_data().values():
        if user.is_system_user():
            continue
        yield CreateUserStrategy(seq, user.get_create_date(), ADMIN_USER,
                                 [user.get_identity(), user.get_name()],
                                 source.get_settings())
        seq += 1
        for backlog in user.values():
            yield CreateBacklogStrategy(seq, backlog.get_create_date(), user.get_identity(),
                                        [backlog.get_uid(), backlog.get_name()],
                                        source.get_settings())
            seq += 1
            for workitem in backlog.values():
                yield CreateWorkitemStrategy(seq, workitem.get_create_date(), user.get_identity(),
                                             [workitem.get_uid(), backlog.get_uid(), workitem.get_name()],
                                             source.get_settings())
                seq += 1
                for pomodoro in workitem.values():
                    # We could create all at once, but then we'd lose the information about unplanned pomodoros
                    yield AddPomodoroStrategy(seq, workitem.get_create_date(), user.get_identity(),
                                              [workitem.get_uid(), '1'],
                                              source.get_settings())
                    seq += 1
                    if pomodoro.is_canceled() or pomodoro.is_finished():
                        yield StartWorkStrategy(seq,
                                                pomodoro.get_last_modified_date() - datetime.timedelta(seconds=1),
                                                user.get_identity(),
                                                [workitem.get_uid(), '1'],
                                                source.get_settings())
                        seq += 1
                    if pomodoro.is_canceled():
                        yield VoidPomodoroStrategy(seq, pomodoro.get_last_modified_date(), user.get_identity(),
                                                   [workitem.get_uid()],
                                                   source.get_settings())
                        seq += 1
                    elif pomodoro.is_finished():
                        yield StartRestStrategy(seq, pomodoro.get_last_modified_date(), user.get_identity(),
                                                [workitem.get_uid(), '1'],
                                                source.get_settings())
                        seq += 1
                if workitem.is_sealed():
                    yield CompleteWorkitemStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                   [workitem.get_uid(), 'finished'],
                                                   source.get_settings())
                    seq += 1


def merge_strategies(source: AbstractEventSource[TRoot],
                     data: TRoot) -> Iterable[AbstractStrategy]:
    """The list of strategies required to merge self with another, used in import"""

    # Prepare maps to speed up imports, otherwise we'll have to loop a lot
    existing_backlogs = dict[str, Backlog]()
    for backlog in source.backlogs():
        existing_backlogs[backlog.get_uid()] = backlog
    existing_workitems = dict[str, Workitem]()
    for workitem in source.workitems():
        existing_workitems[workitem.get_uid()] = workitem

    seq = source.get_last_sequence() + 1
    for user in data.values():
        if user.is_system_user():
            continue
        if user.get_identity() not in source.get_data():
            yield CreateUserStrategy(seq, user.get_create_date(), ADMIN_USER,
                                     [user.get_identity(), user.get_name()],
                                     source.get_settings())
            seq += 1
        else:
            # Check if it was renamed
            existing_user: User = source.get_data()[user.get_identity()]
            if user.get_name() != existing_user.get_name():
                if user.get_last_modified_date() > existing_user.get_last_modified_date():
                    yield RenameUserStrategy(seq, user.get_last_modified_date(), ADMIN_USER,
                                             [user.get_identity(), user.get_name()],
                                             source.get_settings())
                    seq += 1

        for backlog in user.values():
            if backlog.get_uid() not in existing_backlogs:
                yield CreateBacklogStrategy(seq, backlog.get_create_date(), user.get_identity(),
                                            [backlog.get_uid(), backlog.get_name()],
                                            source.get_settings())
                seq += 1
            else:
                # Check if it was renamed
                existing_backlog = existing_backlogs[backlog.get_uid()]
                if backlog.get_name() != existing_backlog.get_name():
                    if backlog.get_last_modified_date() > existing_backlog.get_last_modified_date():
                        yield RenameBacklogStrategy(seq, backlog.get_last_modified_date(), user.get_identity(),
                                                    [backlog.get_uid(), backlog.get_name()],
                                                    source.get_settings())
                        seq += 1

            for workitem in backlog.values():
                if workitem.get_uid() not in existing_workitems:
                    yield CreateWorkitemStrategy(seq, workitem.get_create_date(), user.get_identity(),
                                                 [workitem.get_uid(), backlog.get_uid(), workitem.get_name()],
                                                 source.get_settings())
                    seq += 1
                    existing_workitem = existing_workitems[workitem.get_uid()]
                else:
                    # Check if it was renamed
                    existing_workitem = existing_workitems[workitem.get_uid()]
                    if workitem.get_name() != existing_workitem.get_name():
                        if workitem.get_last_modified_date() > existing_workitem.get_last_modified_date():
                            yield RenameWorkitemStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                         [workitem.get_uid(), workitem.get_name()],
                                                         source.get_settings())
                            seq += 1
                    if existing_workitem.has_running_pomodoro():
                        yield VoidPomodoroStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                   [workitem.get_uid()],
                                                   source.get_settings())
                        seq += 1

                # Merge pomodoros by adding the new ones and completing some, if needed
                num_pomodoros_to_add = len(workitem) - len(existing_workitem)
                if num_pomodoros_to_add > 0:
                    yield AddPomodoroStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                              [workitem.get_uid(), str(num_pomodoros_to_add)],
                                              source.get_settings())
                    seq += 1

                # Here we rely on dict.values() having list semantics. Need to check if this is guaranteed behavior.
                # Also, we rely on the fact that there are at least len(workitem) pomodoros now
                pomodoros_old = list(existing_workitem.values())
                for i, p_new in enumerate(workitem.values()):
                    p_old = pomodoros_old[i]
                    if p_old.is_startable():
                        if p_new.is_canceled() or p_new.is_finished():
                            yield StartWorkStrategy(seq,
                                                    p_new.get_last_modified_date() - datetime.timedelta(seconds=1),
                                                    user.get_identity(),
                                                    [workitem.get_uid(), '1'],
                                                    source.get_settings())
                            seq += 1
                            if p_new.is_canceled():
                                yield VoidPomodoroStrategy(seq, p_new.get_last_modified_date(), user.get_identity(),
                                                           [workitem.get_uid()],
                                                           source.get_settings())
                                seq += 1
                            if p_new.is_finished():
                                yield StartRestStrategy(seq, p_new.get_last_modified_date(), user.get_identity(),
                                                        [workitem.get_uid(), '1'],
                                                        source.get_settings())
                                seq += 1

                if workitem.is_sealed() and (existing_workitem is None or not existing_workitem.is_sealed()):
                    yield CompleteWorkitemStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                   [workitem.get_uid(), 'finished'],
                                                   source.get_settings())
                    seq += 1


def _export_compressed(source: AbstractEventSource[TRoot],
                       another: AbstractEventSource[TRoot],
                       export_file,
                       completion_callback: Callable[[int], None],
                       export_serializer: AbstractSerializer) -> None:
    for strategy in compressed_strategies(source):
        serialized = export_serializer.serialize(strategy)
        export_file.write(f'{serialized}\n')
    _export_completed(source, another, export_file, completion_callback)


def export(source: AbstractEventSource[TRoot],
           filename: str,
           new_root: TRoot,
           encrypt: bool,
           compress: bool,
           start_callback: Callable[[int], None],
           progress_callback: Callable[[int, int], None],
           completion_callback: Callable[[int], None]) -> None:
    export_serializer = create_export_serializer(source, encrypt)
    another = source.clone(new_root)
    every = max(int(source._estimated_count / 100), 1)
    export_file = open(filename, 'w', encoding='UTF-8')

    if compress:
        another.on(events.SourceMessagesProcessed,
                   lambda **kwargs: _export_compressed(source,
                                                       another,
                                                       export_file,
                                                       completion_callback,
                                                       export_serializer))
    else:
        another.on(events.AfterMessageProcessed,
                   lambda strategy, auto, **kwargs: None if auto else _export_message_processed(source,
                                                                                                another,
                                                                                                export_file,
                                                                                                progress_callback,
                                                                                                every,
                                                                                                strategy,
                                                                                                export_serializer))
        another.on(events.SourceMessagesProcessed,
                   lambda **kwargs: _export_completed(source,
                                                      another,
                                                      export_file,
                                                      completion_callback))

    start_callback(source._estimated_count)
    another.start(mute_events=False)


def create_export_serializer(source: AbstractEventSource[TRoot], encrypt=False) -> AbstractSerializer:
    if encrypt:
        return SimpleSerializer(source.get_settings(), source._cryptograph)
    else:
        return SimpleSerializer(source.get_settings(), NoCryptograph(source.get_settings()))


def import_(source: AbstractEventSource[TRoot],
            filename: str,
            ignore_errors: bool,
            merge: bool,
            start_callback: Callable[[int], None],
            progress_callback: Callable[[int, int], None],
            completion_callback: Callable[[int], None]) -> None:
    if merge:
        # 1. Read import file by doing a classic import on an ephemeral source
        settings = MockSettings(username=source.get_settings().get_username(),
                                source_type='ephemeral')
        new_source = EventSourceHolder(settings, NoCryptograph(settings)).request_new_source()
        import_classic(new_source,
                       filename,
                       ignore_errors,
                       start_callback,
                       progress_callback,
                       lambda total: _merge_sources(source, new_source, completion_callback))  # Step 2 is done there
    else:
        import_classic(source, filename, ignore_errors, start_callback, progress_callback, completion_callback)


def _merge_sources(existing_source,
                   new_source,
                   completion_callback: Callable[[int], None]) -> None:
    # 2. Execute the "merge" sequence of strategies obtained via source.merge_strategies()
    count = 0
    existing_source.mute()
    for strategy in merge_strategies(existing_source, new_source.get_data()):
        existing_source.execute_prepared_strategy(strategy, False, True)
        count += 1
    existing_source.unmute()
    completion_callback(count)


def import_classic(source: AbstractEventSource[TRoot],
                   filename: str,
                   ignore_errors: bool,
                   start_callback: Callable[[int], None],
                   progress_callback: Callable[[int, int], None],
                   completion_callback: Callable[[int], None]) -> None:
    # Note that this method ignores sequences and will import even "broken" files
    if not path.isfile(filename):
        raise Exception(f'File {filename} not found')

    with open(filename, 'rb') as f:
        total = sum(1 for _ in f)
        every = max(int(total / 100), 1)

    start_callback(total)
    source.mute()

    user_identity = source.get_settings().get_username()
    i = 0

    if user_identity not in source.users():
        i += 1
        strategy = CreateUserStrategy(i,
                                      datetime.datetime.now(datetime.timezone.utc),
                                      ADMIN_USER,
                                      [user_identity, source.get_settings().get_fullname()],
                                      source.get_settings())
        try:
            source.execute_prepared_strategy(strategy, False, True)
        except Exception as e:
            if ignore_errors:
                logger.warning('Ignored an error while importing', exc_info=e)
            else:
                raise e

    # With encrypt=True it will try to deserialize as much as possible
    export_serializer = create_export_serializer(source, True)

    with open(filename, encoding='UTF-8') as f:
        for line in f:
            try:
                strategy = export_serializer.deserialize(line)
                strategy.replace_user_identity(user_identity)
                if strategy is None or type(strategy) is CreateUserStrategy:
                    continue
                i += 1
                source.execute_prepared_strategy(strategy, False, True)
                if i % every == 0:
                    progress_callback(i, total)
            except Exception as e:
                if ignore_errors:
                    logger.warning('Ignored an error while importing', exc_info=e)
                else:
                    raise e

    source.auto_seal()
    source.unmute()
    completion_callback(total)

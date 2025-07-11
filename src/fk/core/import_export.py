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
from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_serializer import AbstractSerializer
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import CreateBacklogStrategy, RenameBacklogStrategy
from fk.core.event_source_holder import EventSourceHolder
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.pomodoro_strategies import AddPomodoroStrategy, AddInterruptionStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tags import sanitize_tag
from fk.core.tenant import ADMIN_USER
from fk.core.timer_strategies import StopTimerStrategy, StartTimerStrategy
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
        # UC-2: Export progress is displayed through the progress bar
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
    # UC-2: Export can compress strategies to the bare minimum without losing crucial timestamps.

    strategies = list[AbstractStrategy]()

    for user in source.get_data().values():
        if user.is_system_user():
            continue
        strategies.append(
            CreateUserStrategy(0,
                               user.get_create_date(),
                               ADMIN_USER,
                                 [user.get_identity(), user.get_name()],
                                 source.get_settings()))

        for backlog in user.values():
            strategies.append(
                CreateBacklogStrategy(0,
                                      backlog.get_create_date(),
                                      user.get_identity(),
                                        [backlog.get_uid(), backlog.get_name()],
                                        source.get_settings()))

            for workitem in backlog.values():
                strategies.append(
                    CreateWorkitemStrategy(0,
                                           workitem.get_create_date(),
                                           user.get_identity(),
                                             [workitem.get_uid(), backlog.get_uid(), workitem.get_name()],
                                             source.get_settings()))

                for pomodoro in workitem.values():
                    # We could create all at once, but then we'd lose the information about unplanned pomodoros
                    strategies.append(
                        AddPomodoroStrategy(0,
                                            pomodoro.get_create_date(),
                                            user.get_identity(),
                                              [workitem.get_uid(), '1', pomodoro.get_type()],
                                              source.get_settings()))

                    for interruption in pomodoro.values():
                        strategies.append(
                            AddInterruptionStrategy(0,
                                                    interruption.get_create_date(),
                                                    user.get_identity(),
                                                    [
                                                        workitem.get_uid(),
                                                        interruption.get_reason() if interruption.get_reason() is not None else '',
                                                        str(interruption.get_duration().total_seconds()) if interruption.get_duration() is not None else ''],
                                                    source.get_settings()))

                for interval in workitem.get_intervals():
                    strategies.append(
                        StartTimerStrategy(0,
                                           interval.get_started(),
                                           user.get_identity(),
                                           [
                                               workitem.get_uid(),
                                               str(interval.get_work_duration()),
                                               str(interval.get_rest_duration())],
                                           source.get_settings()))

                    if interval.is_ended_manually():
                        strategies.append(
                            StopTimerStrategy(0,
                                              interval.get_ended(),
                                              user.get_identity(),
                                              [],
                                              source.get_settings()))

                if workitem.is_sealed():
                    strategies.append(
                        CompleteWorkitemStrategy(0,
                                                 workitem.get_last_modified_date(),
                                                 user.get_identity(),
                                                 [
                                                     workitem.get_uid(),
                                                     'finished'],
                                                 source.get_settings()))

    strategies.sort(key=lambda x: x.get_when())
    seq = 1
    for s in strategies:
        s.update_sequence(seq)
        seq += 1
        yield s


def merge_strategies(source: AbstractEventSource[TRoot],
                     data: TRoot) -> Iterable[AbstractStrategy]:
    """The list of strategies required to merge self with another, used in import. Here source is the "into" / combined
    source, and "data" is the result of loading import file into a new empty source."""
    # UC-2: Import can be done incrementally ("smart import"). Such an import should never delete anything. Items with the same UIDs will be merged together.

    # Prepare maps to speed up imports, otherwise we'll have to loop a lot
    existing_backlogs = dict[str, Backlog]()
    for backlog in source.backlogs():
        existing_backlogs[backlog.get_uid()] = backlog
    existing_workitems = dict[str, Workitem]()
    for workitem in source.workitems():
        existing_workitems[workitem.get_uid()] = workitem

    strategies = list[AbstractStrategy]()

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
                    existing_workitem = source.find_workitem(workitem.get_uid())
                else:
                    # Check if it was renamed
                    existing_workitem = existing_workitems[workitem.get_uid()]
                    if workitem.get_name() != existing_workitem.get_name():
                        if workitem.get_last_modified_date() > existing_workitem.get_last_modified_date():
                            # UC-3: Smart import will rename any named data objects if their last modification date is later in the imported file
                            yield RenameWorkitemStrategy(seq, workitem.get_last_modified_date(), user.get_identity(),
                                                         [workitem.get_uid(), workitem.get_name()],
                                                         source.get_settings())
                            seq += 1

                # Merge pomodoros by adding the new ones and completing some, if needed
                num_pomodoros_to_add = len(workitem) - len(existing_workitem)
                if num_pomodoros_to_add > 0:
                    for p_old in list(workitem.values())[-num_pomodoros_to_add:]:
                        # UC-2: Smart import would result in the max(existing, imported) number of pomodoros for each workitem
                        yield AddPomodoroStrategy(seq,
                                                  p_old.get_create_date(),
                                                  user.get_identity(),
                                                  [
                                                      workitem.get_uid(),
                                                      '1',
                                                      p_old.get_type()],
                                                  source.get_settings())
                        seq += 1

                # From here on we are adding strategies to the list instead of yielding them directly,
                # because they must be sorted by time. StartTimer on another workitem might come in the
                # middle between StartTimer on _this_ one.

                # We start with interruptions, because for the voided pomodoros their timestamps are
                # identical to StopTimer ones, so if we do the Intervals first, we'd have "workitem
                # is not running" errors.
                pomodoros_old = list(existing_workitem.values())
                for i, p_new in enumerate(workitem.values()):
                    # Here we rely on the fact that because we yielded AddPomodoros above, there
                    # are at least len(workitem) pomodoros now, so we won't go out of array bounds
                    p_old = pomodoros_old[i]

                    # Import interruptions similarly to pomodoros
                    for interruption in p_new.values():
                        if interruption not in p_old.values():
                            strategies.append(
                                AddInterruptionStrategy(0,
                                                        interruption.get_create_date(),
                                                        user.get_identity(),
                                                        [
                                                            workitem.get_uid(),
                                                            interruption.get_reason() if interruption.get_reason() is not None else '',
                                                            str(interruption.get_duration().total_seconds()) if interruption.get_duration() is not None else ''],
                                                        source.get_settings()))

                for interval in workitem.get_intervals():
                    if interval not in existing_workitem.get_intervals():
                        strategies.append(
                            StartTimerStrategy(0,
                                               interval.get_started(),
                                               user.get_identity(),
                                               [
                                                   workitem.get_uid(),
                                                   str(interval.get_work_duration()),
                                                   str(interval.get_rest_duration())],
                                               source.get_settings()))

                        if interval.is_ended_manually():
                            strategies.append(
                                StopTimerStrategy(0,
                                                  interval.get_ended(),
                                                  user.get_identity(),
                                                  [],
                                                  source.get_settings()))

                if workitem.is_sealed() and (existing_workitem is None or not existing_workitem.is_sealed()):
                    strategies.append(
                        CompleteWorkitemStrategy(0,
                                                 workitem.get_last_modified_date(),
                                                 user.get_identity(),
                                                 [
                                                     workitem.get_uid(),
                                                     'finished'],
                                                 source.get_settings()))

        strategies.sort(key=lambda x: x.get_when())
        for s in strategies:
            s.update_sequence(seq)
            seq += 1
            yield s


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
        # UC-2: The user can choose to export data unencrypted
        # UC-2: The user can choose to export data encrypted. The current e2e encryption key is used.
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
        new_source_holder = EventSourceHolder(settings, NoCryptograph(settings))
        import_classic(new_source_holder.request_new_source(),
                       filename,
                       ignore_errors,
                       start_callback,
                       progress_callback,
                       lambda total: _merge_sources(source,  # Step 2 is done there
                                                    new_source_holder,
                                                    ignore_errors,
                                                    completion_callback))
    else:
        import_classic(source,
                       filename,
                       ignore_errors,
                       start_callback,
                       progress_callback,
                       completion_callback)


def import_github_issues(source: AbstractEventSource[TRoot],
                         name: str,
                         issues: list[object],
                         tag_creator: bool,
                         tag_assignee: bool,
                         tag_labels: bool,
                         tag_milestone: bool,
                         tag_state: bool) -> str:
    log = ''
    found: Backlog = None

    user: User = source.get_data().get_current_user()
    for b in user.values():
        if b.get_name() == name:
            found = b
            log = f'Found existing backlog "{name}"\n'
            break

    if found is None:
        b_uid = generate_uid()
        source.execute(CreateBacklogStrategy, [b_uid, name])
        found = user[b_uid]
        log = f'Created backlog "{name}"\n'

    created = 0
    updated = 0
    skipped = 0
    for issue in issues:
        title = f'{issue["number"]} - {issue["title"]}'

        # Check if such workitem already exists
        existing: Workitem = None
        for wi in found.values():
            if wi.get_name().startswith(title):
                existing = wi
                break

        if existing is not None and existing.is_sealed():
            skipped += 1
            continue    # Nothing we can do with it

        tags = ''
        if tag_creator and issue.get('user', None) is not None:
            tags += ' #' + sanitize_tag(issue['user']['login'])
        if tag_assignee and issue.get('assignee', None) is not None:
            tags += ' #' + sanitize_tag(issue['assignee']['login'])
        if tag_labels and issue.get('labels', None) is not None:
            for label in issue['labels']:
                tags += ' #' + sanitize_tag(label['name'])
        if tag_milestone and issue.get('milestone', None) is not None:
            tags += ' #' + sanitize_tag(issue['milestone']['title'])
        if tag_state and issue.get('state', None) is not None:
            tags += ' #' + sanitize_tag(issue['state'])
        if tags != '':
            title += f' [ {tags[1:]} ]'

        if existing is not None and existing.get_name() == title:
            skipped += 1
            continue    # Nothing to do

        if existing is None:
            w_uid = generate_uid()
            source.execute(CreateWorkitemStrategy, [w_uid, found.get_uid(), title])
            created += 1
        else:
            source.execute(RenameWorkitemStrategy, [existing.get_uid(), title])
            updated += 1


    if created == 0:
        log += 'Did not create any new work items\n'
    else:
        log += f'Created {created} work items\n'

    if skipped > 0:
        log += f'Skipped {skipped} existing work items\n'

    if updated > 0:
        log += f'Updated {updated} existing work items\n'

    return log


def import_simple(source: AbstractEventSource[TRoot],
                  tasks: dict[str, list[object]]) -> str:
    log = ''
    user: User = source.get_data().get_current_user()

    for name in tasks.keys():
        found: Backlog = None
        for b in user.values():
            if b.get_name() == name:
                found = b
                log = f'Found existing backlog "{name}"\n'
                break

        if found is None:
            b_uid = generate_uid()
            source.execute(CreateBacklogStrategy, [b_uid, name])
            found = user[b_uid]
            log = f'Created backlog "{name}"\n'

        created = 0
        skipped = 0
        completed = 0
        for task in tasks[name]:
            title = task[0]
            state = task[1]

            # Check if such workitem already exists
            existing: Workitem = None
            for wi in found.values():
                if wi.get_name() == title:
                    existing = wi
                    break

            if existing is None:
                w_uid = generate_uid()
                source.execute(CreateWorkitemStrategy, [w_uid, found.get_uid(), title])
                existing = found[w_uid]
                created += 1
            else:
                w_uid = existing.get_uid()
                skipped += 1

            if state == 'completed' and not existing.is_sealed():
                source.execute(CompleteWorkitemStrategy, [w_uid, 'finished'])
                completed += 1

        if created == 0:
            log += ' - Did not create any new work items\n'
        else:
            log += f' - Created {created} work items\n'

        if skipped > 0:
            log += f' - Skipped {skipped} existing work items\n'

        if completed > 0:
            log += f' - Marked {completed} work items as completed\n'

        log += '\n'

    return log


def _merge_sources(existing_source,
                   new_source_holder,
                   ignore_errors,
                   completion_callback: Callable[[int], None]) -> None:
    # 2. Execute the "merge" sequence of strategies obtained via source.merge_strategies()
    count = 0
    # UC-3: Any import mutes all events on the existing event source for the duration of the import
    existing_source.mute()
    for strategy in merge_strategies(existing_source, new_source_holder.get_source().get_data()):
        try:
            existing_source.execute_prepared_strategy(strategy, False, True)
        except Exception as e:
            if ignore_errors:
                logger.warning(f'Error while importing data, ignoring: {e}')
            else:
                raise e
        count += 1
    existing_source.unmute()
    new_source_holder.close_current_source()
    completion_callback(count)


def import_classic(source: AbstractEventSource[TRoot],
                   filename: str,
                   ignore_errors: bool,
                   start_callback: Callable[[int], None],
                   progress_callback: Callable[[int, int], None],
                   completion_callback: Callable[[int], None]) -> None:
    # UC-1: Classic import replays strategies from the input file as-is and can therefore delete objects
    # UC-1: Classic import will create duplicates for pomodoros on non-sealed workitems
    # Note that this method ignores sequences and will import even "broken" files
    if not path.isfile(filename):
        # UC-3: Imports should fail if a non-existent filename is supplied
        raise Exception(f'File {filename} not found')

    with open(filename, 'rb') as f:
        total = sum(1 for _ in f)
        every = max(int(total / 100), 1)

    start_callback(total)
    source.mute()

    user_identity = source.get_settings().get_username()
    i = 0

    if source.find_user(user_identity) is None:
        # UC-3: Before classic import, if a user configured in Settings is not in the data model, it is created automatically
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
    # UC-2: Classic import will try to import as many strategies as possible, even if the file is encrypted with another key

    with open(filename, encoding='UTF-8') as f:
        for line in f:
            try:
                strategy = export_serializer.deserialize(line)
                strategy.replace_user_identity(user_identity)
                # UC-3: Classic import replaces user identity on the imported strategies with the current user
                if strategy is None or type(strategy) is CreateUserStrategy:
                    # UC-3: Classic import ignores CreateUser strategies
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

    source.unmute()
    completion_callback(total)

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

import logging
import os
import time
from collections import deque
from os import path
from typing import TypeVar, Iterable

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_filesystem_watcher import AbstractFilesystemWatcher
from fk.core.abstract_settings import AbstractSettings, prepare_file_for_writing
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy, RenameBacklogStrategy
from fk.core.import_export import compressed_strategies
from fk.core.pomodoro_strategies import AddPomodoroStrategy, RemovePomodoroStrategy, AddInterruptionStrategy
from fk.core.simple_serializer import SimpleSerializer
from fk.core.tenant import Tenant, ADMIN_USER
from fk.core.timer_strategies import StartWorkStrategy, StartTimerStrategy
from fk.core.user_strategies import DeleteUserStrategy, CreateUserStrategy, RenameUserStrategy
from fk.core.workitem_strategies import CreateWorkitemStrategy, DeleteWorkitemStrategy, RenameWorkitemStrategy, \
    CompleteWorkitemStrategy, ReorderWorkitemStrategy, MoveWorkitemStrategy

logger = logging.getLogger(__name__)
TRoot = TypeVar('TRoot')


class FileEventSource(AbstractEventSource[TRoot]):
    _data: TRoot
    _watcher: AbstractFilesystemWatcher | None
    _existing_strategies: Iterable[AbstractStrategy] | None
    _last_strategy: AbstractStrategy | None

    def __init__(self,
                 settings: AbstractSettings,
                 cryptograph: AbstractCryptograph,
                 root: TRoot,
                 filesystem_watcher: AbstractFilesystemWatcher = None,
                 existing_strategies: Iterable[AbstractStrategy] | None = None):
        super().__init__(SimpleSerializer(settings, cryptograph),
                         settings,
                         cryptograph)
        logger.debug(f'Created FileEventSource with serializer {self._serializer}')
        self._data = root
        self._watcher = None
        self._existing_strategies = existing_strategies
        self._last_strategy = None
        if self._is_watch_changes() and filesystem_watcher is not None:
            self._watcher = filesystem_watcher
            self._watcher.watch(self._get_filename(), self._on_file_change)

    def get_last_strategy(self) -> AbstractStrategy | None:
        return self._last_strategy

    def _on_file_change(self, filename: str) -> None:
        # This method is called when we get updates from "remote"
        logger.info(f'Data file content changed: {filename}')
        # UC-1: File event source: If file watching is enabled, the strategies with the sequence > last_seq are executed
        # UC-3: Any event source fires all events for the incremental processing
        # We open the file as r+ to make sure that another process finished writing and
        # released the file handler. By default, OSes won't allow concurrent writes to the
        # file, so if something is still writing into it, then this call will fail.
        with open(filename, 'r+', encoding='UTF-8') as file:
            last_executed = None
            for line in file:
                try:
                    strategy = self._serializer.deserialize(line)
                    if strategy is None:
                        continue
                    self._last_strategy = strategy
                    seq = strategy.get_sequence()
                    if seq > self._last_seq:
                        if not self._ignore_invalid_sequences and seq != self._last_seq + 1:
                            self._sequence_error(self._last_seq, seq)
                        self._last_seq = seq
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Will execute new strategy: {strategy}")
                        # UC-1: For any event source, whenever it executes a strategy with seq_num != last_seq + 1, and "ignore sequence" settings is disables, it fails
                        self.execute_prepared_strategy(strategy)
                        last_executed = strategy
                except Exception as ex:
                    if self._ignore_errors:
                        logger.warning(f'Error processing {line} (ignored)', exc_info=ex)
                    else:
                        raise ex
                finally:
                    if last_executed is not None:
                        self._auto_seal_at_the_end(last_executed)

    def _get_filename(self) -> str:
        return self.get_config_parameter("FileEventSource.filename")

    def _is_watch_changes(self) -> bool:
        return self.get_config_parameter("FileEventSource.watch_changes") == "True"

    def start(self, mute_events: bool = True, fail_early: bool = False) -> None:
        if self._existing_strategies is None:
            self._process_from_file(mute_events)
        else:
            self._process_from_existing(fail_early)

    # This method is called when we repair an existing data source
    def _process_from_existing(self, fail_early: bool) -> None:
        # UC-2: File event source can be created from the existing pre-parsed strategies.
        #  It behaves just like normal "read file", but without the deserialization checks.
        #  It checks sequences and triggers SourceMessagesRequested events.
        #  All events are muted during processing.
        self._emit(events.SourceMessagesRequested, dict())
        self.mute()
        is_first = True
        last_executed = None
        seq = 1
        for strategy in self._existing_strategies:
            try:
                if strategy is None:
                    continue
                strategy._settings = self._settings
                self._last_strategy = strategy

                seq = strategy.get_sequence()
                if is_first:
                    is_first = False
                else:
                    if (fail_early or not self._ignore_invalid_sequences) and seq != self._last_seq + 1:
                        self._sequence_error(self._last_seq, seq)
                self._last_seq = seq
                self.execute_prepared_strategy(strategy)
                last_executed = strategy
            except Exception as ex:
                if self._ignore_errors and not fail_early:
                    logger.warning(f'Error processing {strategy} (ignored)', exc_info=ex)
                else:
                    raise ex
        self._auto_seal_at_the_end(last_executed)
        self.unmute()
        self._emit(events.SourceMessagesProcessed, {'source': self})

    def _process_from_file(self, mute_events=True) -> None:
        # This method is called when we read the history
        self._emit(events.SourceMessagesRequested, dict(), None)
        if mute_events:
            self.mute()

        filename = self._get_filename()
        if path.isdir(filename):
            raise IsADirectoryError(f'{filename} is a directory. Expected a filename.')
        elif not path.isfile(filename):
            prepare_file_for_writing(filename)
            with open(filename, 'w', encoding='UTF-8') as f:
                s = self.get_init_strategy(self._emit)
                f.write(f'{self._serializer.serialize(s)}\n')
                logger.info(f'Created empty data file {filename}')
                # UC-1: The file event source always creates a new file with CreateUser strategy, if it doesn't exist

        is_first = True
        last_executed = None
        seq = 1
        logger.info(f'FileEventSource: Reading file {filename}')
        with open(filename, encoding='UTF-8') as f:
            # TODO: If we wrap this for into a generator, we'll be able to reuse a this entire loop
            #  with _process_from_existing() and _on_file_change()
            for line in f:
                try:
                    strategy = self._serializer.deserialize(line)
                    if strategy is None:
                        continue
                    self._last_strategy = strategy

                    if is_first:
                        is_first = False
                    else:
                        seq = strategy.get_sequence()
                        if not self._ignore_invalid_sequences and seq != self._last_seq + 1:
                            self._sequence_error(self._last_seq, seq)
                    # UC-3: Strategies may start with any sequence number
                    self._last_seq = seq
                    self.execute_prepared_strategy(strategy)
                    last_executed = strategy
                except Exception as ex:
                    if self._ignore_errors:
                        logger.warning(f'Error processing {line} (ignored)', exc_info=ex)
                    else:
                        raise ex
        logger.debug('FileEventSource: Processed file content, will unmute events now')

        # UC-1: The last strategy is auto-sealed after execution to ensure that the timer rings offline, if needed
        self._auto_seal_at_the_end(last_executed)

        # UC-1: Any event source mutes its events for the duration of the first parsing and for the export/import
        if mute_events:
            self.unmute()
        self._emit(events.SourceMessagesProcessed, {'source': self})

    def repair(self) -> tuple[list[str], str | None]:
        # This method attempts some basic repairs, trying to save as much
        # data as possible:
        # 0. Reorder strategies by date
        # 1. Remove duplicate creations
        # 2. Create non-existent users on first reference
        # 3. Create non-existent backlogs on first reference
        # 4. Create non-existent workitems on first reference
        # 5. Renumber strategies
        # 6. Restart and remove failing strategies
        # Perform 5 -- 6 in the loop
        # It will overwrite existing data file and will create a backup with "-backup-<date>" suffix

        # UC-1: File event source can repair any broken source file. It reorders strategies by date, removes duplicates, creates missing data objects on first reference, renumbers strategies, and deletes failing ones.
        # UC-1: After the repair, the file source is guaranteed to load successfully without errors or warnings
        # UC-3: File source repair generates backup files with "-backup-<date>" suffix

        log = list()
        changes: int = 0
        original_watcher = self._watcher
        self._watcher = None

        # Read strategies and repair in one pass
        strategies: deque[AbstractStrategy] = deque()
        all_users: dict[str, set[str]] = dict()
        all_backlogs: dict[str, set[str]] = dict()
        all_workitems: set[str] = set()
        repaired_backlog: str | None = None

        parsed = list[AbstractStrategy]()
        with open(self._get_filename(), encoding='UTF-8') as f:
            for line in f:
                try:
                    s = self._serializer.deserialize(line)
                    if s:
                        parsed.append(s)
                except Exception as ex:
                    log.append(f'Skipped invalid strategy ({ex}): {line}')
                    changes += 1
                    continue

        # Reorder strategies by timestamp
        sorted_strategies = sorted(parsed, key=lambda x: x.get_when())
        for i, s in enumerate(parsed):
            if sorted_strategies[i] != s:
                changes += 1
                log.append(f'Reordered strategies')
                parsed = deque[AbstractStrategy](sorted_strategies)
                break

        for s in parsed:
            t = type(s)

            # Create users on the first reference
            uid = s.get_user_identity()
            if t is not CreateUserStrategy and uid not in all_users:
                strategies.append(CreateUserStrategy(1,
                                                     s._when,
                                                     ADMIN_USER,
                                                     [uid, f"[Repaired] {uid}"],
                                                     self._settings))
                all_users[uid] = set()
                log.append(f'Created a missing user on first reference: {uid}')
                changes += 1
            if t is CreateUserStrategy:
                cast: CreateUserStrategy = s
                uid = cast.get_target_user_identity()
                if uid in all_users:   # Remove duplicate creation
                    log.append(f'Skipped a duplicate user: {uid}')
                    changes += 1
                    continue
                all_users[uid] = set()
            elif t is DeleteUserStrategy:
                cast: DeleteUserStrategy = s
                uid = cast.get_target_user_identity()
                if uid not in all_users:
                    log.append(f'Skipped deletion of a non-existent user: {uid}')
                    changes += 1
                    continue

                # Remove all user's backlogs with their content recursively
                for backlog_uid in all_users[uid]:
                    if backlog_uid in all_backlogs:
                        for workitem_uid in all_backlogs[backlog_uid]:
                            if workitem_uid in all_workitems:
                                all_workitems.remove(workitem_uid)
                        del all_backlogs[backlog_uid]
                del all_users[uid]

            elif t is RenameUserStrategy:
                cast: RenameUserStrategy = s
                uid = cast.get_target_user_identity()
                if uid not in all_users:
                    strategies.append(CreateUserStrategy(1,
                                                         s._when,
                                                         ADMIN_USER,
                                                         [uid, f"[Repaired] {uid}"],
                                                         self._settings))
                    all_users[uid] = set()
                    log.append(f'Created a missing user on first reference: {uid}')
                    changes += 1

            # Create backlogs on the first reference
            elif t is CreateBacklogStrategy:
                cast: CreateBacklogStrategy = s
                uid = cast.get_backlog_uid()
                if uid in all_backlogs:   # Remove duplicate creation
                    log.append(f'Skipped a duplicate backlog: {uid}')
                    changes += 1
                    continue
                all_backlogs[uid] = set()
            elif t is DeleteBacklogStrategy:
                cast: DeleteBacklogStrategy = s
                uid = cast.get_backlog_uid()
                if uid not in all_backlogs:
                    log.append(f'Skipped deletion of a non-existent backlog: {uid}')
                    changes += 1
                    continue

                # Remove all child workitems recursively
                for workitem_uid in all_backlogs[uid]:
                    if workitem_uid in all_workitems:
                        all_workitems.remove(workitem_uid)
                del all_backlogs[uid]

            elif t is RenameBacklogStrategy or t is CreateWorkitemStrategy:
                cast: RenameBacklogStrategy | CreateWorkitemStrategy = s
                uid = cast.get_backlog_uid()
                if uid not in all_backlogs:
                    strategies.append(CreateBacklogStrategy(1,
                                                            s._when,
                                                            s._user_identity,
                                                            [uid, f"[Repaired] {uid}"],
                                                            self._settings))
                    all_backlogs[uid] = set()
                    all_users[s._user_identity].add(uid)
                    log.append(f'Created a missing backlog on first reference: {uid}')
                    changes += 1
                if t is CreateWorkitemStrategy:
                    cast: CreateWorkitemStrategy = s
                    uid = cast.get_workitem_uid()
                    if uid in all_workitems:  # Remove duplicate creation
                        log.append(f'Skipped a duplicate workitem: {uid}')
                        changes += 1
                        continue
                    all_workitems.add(uid)
                    all_backlogs[cast.get_backlog_uid()].add(uid)

            elif t is DeleteWorkitemStrategy:
                cast: DeleteWorkitemStrategy = s
                uid = cast.get_workitem_uid()
                if uid not in all_workitems:
                    log.append(f'Skipped deletion of a non-existent workitem: {uid}')
                    changes += 1
                    continue
                all_workitems.remove(uid)

            # Create workitems on the first reference. All those strategies assume an existing workitem.
            elif t is RenameWorkitemStrategy or \
                    t is CompleteWorkitemStrategy or \
                    t is MoveWorkitemStrategy or \
                    t is ReorderWorkitemStrategy or \
                    t is StartWorkStrategy or \
                    t is StartTimerStrategy or \
                    t is AddInterruptionStrategy or \
                    t is AddPomodoroStrategy or \
                    t is RemovePomodoroStrategy:
                cast: RenameWorkitemStrategy = s
                uid = cast.get_workitem_uid()
                if uid not in all_workitems:
                    if repaired_backlog is None:
                        repaired_backlog = generate_uid()
                        strategies.append(CreateBacklogStrategy(1,
                                                                s._when,
                                                                s._user_identity,
                                                                [repaired_backlog, '[Repaired] Orphan workitems'],
                                                                self._settings))
                        all_backlogs[repaired_backlog] = set()
                        all_users[s._user_identity].add(repaired_backlog)
                        log.append(f'Created a backlog for orphan workitems: {repaired_backlog}')
                        changes += 1
                    strategies.append(CreateWorkitemStrategy(1,
                                                             s._when,
                                                             s._user_identity,
                                                             [uid, repaired_backlog, f"[Repaired] {uid}"],
                                                             self._settings))
                    all_workitems.add(uid)
                    all_backlogs[repaired_backlog].add(uid)
                    log.append(f'Created a missing workitem on first reference: {uid}')
                    changes += 1

            # Handle duplicates and other logic

            strategies.append(s)

        # Now we need to ensure data consistency somehow. Even though all workitems and backlogs might be there,
        # we may still have an issue with removing too many pomodoros or starting sealed workitems. To fix those,
        # it would be easier to just skip the strategies which throw exceptions on parse.
        while True:
            # Renumber strategies
            seq = strategies[0].get_sequence()
            for s in strategies:
                if s is None:
                    continue
                if s.get_sequence() != seq:
                    s._seq = seq
                    changes += 1
                seq += 1
            log.append(f'Renumbered strategies up to {seq}')

            # Restart and remove failing strategies
            new_source = self.clone(Tenant(self._settings), strategies)
            try:
                new_source.start(fail_early=True)
                log.append(f'Tested successfully')
                break   # No exceptions mean we repaired successfully
            except Exception as ex:
                failed = new_source.get_last_strategy()
                log.append(f'Tested with an error: {ex}. Removed failed strategy: {failed.__class__.__name__}')
                strategies.remove(failed)
                changes += 1

        if changes > 0:
            log.append(f'Made {changes} changes in total')
            # UC-2: File event source repair won't do any changes if the source file is correct
            backup_filename = self._overwrite_file(strategies, log)
        else:
            log.append(f'No changes were made')
            backup_filename = None

        self._watcher = original_watcher
        # UC-3: File event source repair returns the log of all changes it made
        return log, backup_filename

    def _overwrite_file(self, strategies: Iterable[AbstractStrategy], log: list[str]) -> str:
        filename = self._get_filename()
        date = round(time.time() * 1000)
        backup_filename = f"{filename}-backup-{date}"
        os.rename(filename, backup_filename)
        log.append(f'Created backup file {backup_filename}')

        # Write it back
        with open(filename, 'w', encoding='UTF-8') as f:
            for s in strategies:
                f.write(self._serializer.serialize(s) + '\n')
        log.append(f'Overwritten original file {filename}')
        return backup_filename

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        # TODO: If compression is enabled and <base>-complete.<ext> file exists,
        #  then append to both files at the same time.
        # UC-2: For file source, new strategies get appended to the file immediately after execution
        if self._watcher is not None:
            self._watcher.unwatch(self._get_filename())
        try:
            with open(self._get_filename(), 'a', encoding='UTF-8') as f:
                for s in strategies:
                    f.write(self._serializer.serialize(s) + '\n')
        finally:
            if self._watcher is not None:
                self._watcher.watch(self._get_filename(), self._on_file_change)

    def get_name(self) -> str:
        return "File"

    def get_data(self) -> TRoot:
        return self._data

    def _count_valid_strategies(self) -> int:
        valid_count = 0
        with open(self._get_filename(), encoding='UTF-8') as f:
            for line in f:
                try:
                    self._serializer.deserialize(line)
                    valid_count += 1
                except Exception as ex:
                    pass    # We just want to count valid strategies in the original file
        return valid_count

    def compress(self) -> list[str]:
        # 1. Creates a full log copy in <base>-complete.<ext>, if it doesn't exist yet.
        # 2. Rewrites the data file by recreating the CURRENT list of backlogs / workitems.
        #    The last strategy's sequence ID will stay the same, and the previous IDs will
        #    be recalculated backwards.
        # 3. Timestamps will correspond to the latest modification dates.

        # UC-1: File event source can compress source files. It removes inaccessible strategies (deleted, encrypted, repeated, etc.), invisible to the end user, and renumbers strategies.
        # UC-1: After compression, the file source is guaranteed to load successfully, faster, and without errors or warnings
        # UC-3: File source compression generates backup files with "-backup-<date>" suffix

        log = list()

        valid_count = self._count_valid_strategies()
        strategies = list(compressed_strategies(self))
        savings = valid_count - len(strategies)
        if valid_count > 0 and savings > 0:
            savings_percentage = round(100.0 * savings / valid_count)
            log.append(f'The compressed file contains {savings_percentage}% fewer strategies')
            # UC-3: File event source compression won't do any changes if there's no savings
            self._overwrite_file(strategies, log)
        else:
            log.append(f'No changes were made - the data is already compressed')

        # UC-3: File event source compression returns the log with the % of strategy savings
        return log

    def clone(self, new_root: TRoot, existing_strategies: Iterable[AbstractStrategy] | None = None) -> FileEventSource[TRoot]:
        return FileEventSource[TRoot](self._settings,
                                      self._cryptograph,
                                      new_root,
                                      self._watcher,
                                      existing_strategies)

    def disconnect(self):
        if self._watcher is not None:
            self._watcher.unwatch(self._get_filename())

    def send_ping(self) -> str | None:
        raise Exception("FileEventSource does not support send_ping()")

    def can_connect(self):
        return False

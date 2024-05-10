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
import os
import time
from collections import deque
from os import path
from typing import Self, TypeVar, Iterable

from fk.core import events
from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_filesystem_watcher import AbstractFilesystemWatcher
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.tenant import Tenant
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy, RenameBacklogStrategy
from fk.core.strategy_factory import strategy_from_string
from fk.core.user_strategies import DeleteUserStrategy, CreateUserStrategy, RenameUserStrategy
from fk.core.workitem_strategies import CreateWorkitemStrategy, DeleteWorkitemStrategy, RenameWorkitemStrategy, \
    CompleteWorkitemStrategy

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
        super().__init__(settings, cryptograph)
        self._data = root
        self._watcher = None
        self._existing_strategies = existing_strategies
        self._last_strategy = None
        if self._is_watch_changes() and filesystem_watcher is not None:
            self._watcher = filesystem_watcher
            self._watcher.watch(self._get_filename(), lambda f: self._on_file_change(f))

    def get_last_strategy(self) -> AbstractStrategy | None:
        return self._last_strategy

    def _on_file_change(self, filename: str) -> None:
        # This method is called when we get updates from "remote"
        print(f'Data file content changed: {filename}')

        # When we execute strategies here, events are emitted.
        # TODO: Check file locks here?
        with open(filename, encoding='UTF-8') as file:
            for line in file:
                strategy = strategy_from_string(line, self._emit, self.get_data(), self._settings, self._cryptograph)
                if type(strategy) is str:
                    continue
                self._last_strategy = strategy
                seq = strategy.get_sequence()
                if seq > self._last_seq:
                    if seq != self._last_seq + 1:
                        self._sequence_error(self._last_seq, seq)
                    self._last_seq = seq
                    # print(f" - {strategy}")
                    self.execute_prepared_strategy(strategy)
        self.auto_seal()

    def _get_filename(self) -> str:
        return self.get_config_parameter("FileEventSource.filename")

    def _is_watch_changes(self) -> bool:
        return self.get_config_parameter("FileEventSource.watch_changes") == "True"

    def start(self, mute_events=True) -> None:
        if self._existing_strategies is None:
            self._process_from_file(mute_events)
        else:
            self._process_from_existing()

    def _process_from_existing(self) -> None:
        # This method is called when we repair an existing data source
        # All events are muted during processing
        self._emit(events.SourceMessagesRequested, dict())
        self.mute()
        is_first = True
        seq = 1
        for strategy in self._existing_strategies:
            strategy._data = self._data
            strategy._settings = self._settings
            strategy._emit_func = self._emit
            if type(strategy) is str:
                continue
            self._last_strategy = strategy

            if is_first:
                is_first = False
            else:
                seq = strategy.get_sequence()
                if seq != self._last_seq + 1:
                    self._sequence_error(self._last_seq, seq)
            self._last_seq = seq
            self.execute_prepared_strategy(strategy)
        self.auto_seal()
        self.unmute()
        self._emit(events.SourceMessagesProcessed, {'source': self})

    def _process_from_file(self, mute_events=True) -> None:
        # This method is called when we read the history
        self._emit(events.SourceMessagesRequested, dict())
        if mute_events:
            self.mute()

        filename = self._get_filename()
        if not path.isfile(filename):
            with open(filename, 'w', encoding='UTF-8') as f:
                s = self.get_data().get_init_strategy(self._emit)
                f.write(f'{s}\n')
                print(f'Created empty data file {filename}')

        is_first = True
        seq = 1
        print(f'FileEventSource: Reading file {filename}')
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                strategy = strategy_from_string(line, self._emit, self.get_data(), self._settings, self._cryptograph)
                if type(strategy) is str:
                    continue
                self._last_strategy = strategy

                if is_first:
                    is_first = False
                else:
                    seq = strategy.get_sequence()
                    if seq != self._last_seq + 1:
                        self._sequence_error(self._last_seq, seq)
                self._last_seq = seq
                self.execute_prepared_strategy(strategy)
        print('FileEventSource: Processed file content, will auto-seal now')

        self.auto_seal()
        print('FileEventSource: Sealed, will unmute events now')

        if mute_events:
            self.unmute()
        self._emit(events.SourceMessagesProcessed, {'source': self})

    def repair(self) -> Iterable[str]:
        # This method attempts some basic repairs, trying to save as much
        # data as possible:
        # 0. Remove duplicate creations
        # 1. Create non-existent users on first reference
        # 2. Create non-existent backlogs on first reference
        # 3. Create non-existent workitems on first reference
        # 4. Renumber strategies
        # 5. Restart and remove failing strategies
        # Perform 4 -- 5 in the loop
        # It will overwrite existing data file and will create a backup with "-backup-<date>" suffix

        log = list()
        changes: int = 0
        original_watcher = self._watcher
        self._watcher = None

        # Read strategies and repair in one pass
        filename = self._get_filename()
        strategies: deque[AbstractStrategy] = deque()
        all_users: set[str] = set()
        all_backlogs: set[str] = set()
        all_workitems: set[str] = set()
        repaired_backlog: str = None
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                try:
                    s = strategy_from_string(line, self._emit, self._data, self._settings, self._cryptograph)
                except Exception as ex:
                    log.append(f'Skipped invalid strategy ({ex}): {s}')
                    changes += 1
                    continue
                t = type(s)

                # Create users on the first reference
                if t is CreateUserStrategy:
                    cast: CreateUserStrategy = s
                    if cast.get_user_identity() in all_users:   # Remove duplicate creation
                        log.append(f'Skipped duplicate user: {s}')
                        changes += 1
                        continue
                    all_users.add(cast.get_user_identity())
                elif t is DeleteUserStrategy or t is RenameUserStrategy:
                    cast: DeleteUserStrategy | RenameUserStrategy = s
                    uid = cast.get_user_identity()
                    if uid not in all_users:
                        strategies.append(CreateUserStrategy(1,
                                                             s._when,
                                                             s._user,
                                                             [uid, f"[Repaired] {uid}"],
                                                             self._emit,
                                                             self._data,
                                                             self._settings))
                        all_users.add(uid)
                        log.append(f'Created missing user on first reference: {s}')
                        changes += 1

                # Create backlogs on the first reference
                elif t is CreateBacklogStrategy:
                    cast: CreateBacklogStrategy = s
                    if cast.get_backlog_uid() in all_backlogs:   # Remove duplicate creation
                        log.append(f'Skipped duplicate backlog: {s}')
                        changes += 1
                        continue
                    all_backlogs.add(cast.get_backlog_uid())
                elif t is DeleteBacklogStrategy or t is RenameBacklogStrategy or t is CreateWorkitemStrategy:
                    cast: DeleteBacklogStrategy | RenameBacklogStrategy | CreateWorkitemStrategy = s
                    uid = cast.get_backlog_uid()
                    if uid not in all_backlogs:
                        strategies.append(CreateBacklogStrategy(1,
                                                             s._when,
                                                             s._user,
                                                             [uid, f"[Repaired] {uid}"],
                                                             self._emit,
                                                             self._data,
                                                             self._settings))
                        all_backlogs.add(uid)
                        log.append(f'Created missing backlog on first reference: {s}')
                        changes += 1
                    if t is CreateWorkitemStrategy:
                        cast: CreateWorkitemStrategy = s
                        if cast.get_workitem_uid() in all_workitems:  # Remove duplicate creation
                            log.append(f'Skipped duplicate workitem: {s}')
                            changes += 1
                            continue
                        all_workitems.add(cast.get_workitem_uid())

                # Create workitems on the first reference
                elif t is DeleteWorkitemStrategy or t is RenameWorkitemStrategy or t is CompleteWorkitemStrategy:
                    cast: DeleteWorkitemStrategy | RenameWorkitemStrategy | CompleteWorkitemStrategy = s
                    uid = cast.get_workitem_uid()
                    if uid not in all_workitems:
                        if repaired_backlog is None:
                            repaired_backlog = generate_uid()
                            strategies.append(CreateBacklogStrategy(1,
                                                                    s._when,
                                                                    s._user,
                                                                    [repaired_backlog, '[Repaired] Orphan workitems'],
                                                                    self._emit,
                                                                    self._data,
                                                                    self._settings))
                            all_backlogs.add(repaired_backlog)
                            log.append(f'Created a backlog for orphan workitems: {repaired_backlog}')
                            changes += 1
                        strategies.append(CreateWorkitemStrategy(1,
                                                             s._when,
                                                             s._user,
                                                             [uid, repaired_backlog, f"[Repaired] {uid}"],
                                                             self._emit,
                                                             self._data,
                                                             self._settings))
                        all_workitems.add(uid)
                        log.append(f'Created missing workitem on first reference: {s}')
                        changes += 1

                strategies.append(s)

        while True:
            # Renumber strategies
            seq = strategies[0].get_sequence()
            for s in strategies:
                if type(s) is str:
                    continue
                if s.get_sequence() != seq:
                    s._seq = seq
                    changes += 1
                seq += 1
            log.append(f'Renumbered strategies up to {seq}')

            # Restart and remove failing strategies
            new_source = self.clone(Tenant(self._settings), strategies)
            try:
                new_source.start()
                log.append(f'Tested successfully')
                break   # No exceptions means we repaired successfully
            except Exception as ex:
                failed = new_source.get_last_strategy()
                log.append(f'Tested with an error: {ex}. Removed failed strategy: {failed}')
                strategies.remove(failed)
                changes += 1

        if changes > 0:
            log.append(f'Made {changes} changes in total')

            # Rename the original file
            date = round(time.time() * 1000)
            backup_filename = f"{filename}-backup-{date}"
            os.rename(filename, backup_filename)
            log.append(f'Created backup file {backup_filename}')

            # Write it back
            with open(filename, 'w', encoding='UTF-8') as f:
                for s in strategies:
                    f.write(str(s) + '\n')
            log.append(f'Overwritten original file {filename}')
        else:
            log.append(f'No changes were made')

        self._watcher = original_watcher
        return log

    def _append(self, strategies: list[AbstractStrategy]) -> None:
        # TODO: If compression is enabled and <base>-complete.<ext> file exists,
        # then append to both files at the same time.
        with open(self._get_filename(), 'a', encoding='UTF-8') as f:
            for s in strategies:
                f.write(str(s) + '\n')

    def get_name(self) -> str:
        return "File"

    def get_data(self) -> TRoot:
        return self._data

    def compress(self) -> None:
        # 1. Creates a full log copy in <base>-complete.<ext>, if it doesn't exist yet.
        # 2. Rewrites the data file by recreating the CURRENT list of backlogs / workitems.
        #    The last strategy's sequence ID will stay the same, and the previous IDs will
        #    be recalculated backwards.
        # 3. Timestamps will correspond to the latest modification dates.
        # TODO: Implement
        pass

    def clone(self, new_root: TRoot, existing_strategies: Iterable[AbstractStrategy] | None = None) -> Self:
        return FileEventSource(self._settings, self._cryptograph, new_root, self._watcher, existing_strategies)

    def disconnect(self):
        if self._watcher is not None:
            self._watcher.unwatch_all()

    def send_ping(self) -> str | None:
        raise Exception("FileEventSource does not support send_ping()")

    def can_connect(self):
        return False

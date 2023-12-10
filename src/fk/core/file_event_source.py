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

from os import path
from typing import Self, TypeVar

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_filesystem_watcher import AbstractFilesystemWatcher
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.path_resolver import resolve_path
from fk.core.strategy_factory import strategy_from_string

TRoot = TypeVar('TRoot')


class FileEventSource(AbstractEventSource[TRoot]):
    _data: TRoot
    _watcher: AbstractFilesystemWatcher | None

    def __init__(self,
                 settings: AbstractSettings,
                 root: TRoot,
                 filesystem_watcher: AbstractFilesystemWatcher = None):
        super().__init__(settings)
        self._data = root
        self._watcher = None
        if self._is_watch_changes() and filesystem_watcher is not None:
            self._watcher = filesystem_watcher
            self._watcher.watch(self._get_filename(), lambda f: self._on_file_change(f))

    def _on_file_change(self, filename: str) -> None:
        # This method is called when we get updates from "remote"
        print(f'Data file content changed: {filename}')

        # When we execute strategies here, events are emitted.
        # TODO: Check file locks here?
        with open(filename, encoding='UTF-8') as file:
            for line in file:
                strategy = strategy_from_string(line, self._emit, self.get_data(), self._settings)
                if type(strategy) is str:
                    continue
                seq = strategy.get_sequence()
                if seq > self._last_seq:
                    if seq != self._last_seq + 1:
                        raise Exception("Strategies must go in sequence")
                    self._last_seq = seq
                    # print(f" - {strategy}")
                    self._execute_prepared_strategy(strategy)
        self.auto_seal()

    def _get_filename(self) -> str:
        return resolve_path(self.get_config_parameter("FileEventSource.filename"))

    def _is_watch_changes(self) -> bool:
        return self.get_config_parameter("FileEventSource.watch_changes") == "True"

    def start(self, mute_events=True) -> None:
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
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                strategy = strategy_from_string(line, self._emit, self.get_data(), self._settings)
                if type(strategy) is str:
                    continue

                if is_first:
                    is_first = False
                else:
                    seq = strategy.get_sequence()
                    if seq != self._last_seq + 1:
                        raise Exception(f"Strategies must go in sequence ({seq})")
                self._last_seq = seq
                self._execute_prepared_strategy(strategy)
        self.auto_seal()

        if mute_events:
            self.unmute()
        self._emit(events.SourceMessagesProcessed, dict())

    def repair(self) -> None:
        # This method attempts some basic repairs:
        # 1. Renumber strategies
        # It will create a new file with "-repaired" suffix

        # Read all strategies
        filename = self._get_filename()
        strategies = list()
        with open(filename, encoding='UTF-8') as f:
            for line in f:
                s = strategy_from_string(line, self._emit, self.get_data(), self._settings)
                strategies.append(s)

        # Repair
        # 1. Renumber from 1 to N
        seq = 1
        for s in strategies:
            if type(s) is str:
                continue
            s._seq = seq
            seq += 1

        # Write it back
        with open(filename + '-repaired', 'w', encoding='UTF-8') as f:
            for s in strategies:
                f.write(str(s) + '\n')

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

    def clone(self, new_root: TRoot) -> Self:
        return FileEventSource(self._settings, new_root, self._watcher)

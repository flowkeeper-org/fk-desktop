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

import datetime
import logging

from fk.core.abstract_data_item import AbstractDataItem

logger = logging.getLogger(__name__)


class Interruption(AbstractDataItem['Pomodoro']):
    _reason: str | None
    _duration: datetime.timedelta | None
    _void: bool

    def __init__(self,
                 reason: str | None,
                 duration: datetime.timedelta | None,
                 void: bool,
                 uid: str,
                 pomodoro: 'Pomodoro',
                 create_date: datetime.datetime):
        super().__init__(uid=uid, parent=pomodoro, create_date=create_date)
        self._reason = reason
        self._duration = duration
        self._void = void

    def __str__(self):
        if self._reason:
            return f"'[{self._reason}]"
        else:
            return f"'"

    def get_reason(self) -> str | None:
        return self._reason

    def get_duration(self) -> datetime.timedelta | None:
        return self._duration

    def is_void(self) -> bool:
        return (self._void or
                self._reason is not None and self._reason.startswith('Pomodoro voided') or
                self._reason == 'Voided automatically because you completed the workitem while the timer was running.')

    def get_parent(self) -> 'Pomodoro':
        return self._parent

    def dump(self, indent: str = '', mask_uid: bool = False, mask_last_modified: bool = False) -> str:
        return f'{super().dump(indent, True, mask_last_modified)}\n' \
               f'{indent}  Reason: {self._reason if self._reason else "<None>"}\n' \
               f'{indent}  Void: {self._void}\n' \
               f'{indent}  Duration: {self._duration if self._duration else "<None>"}'

    def to_dict(self) -> dict:
        d = super().to_dict()
        d['reason'] = self._reason
        d['duration'] = self._duration
        d['void'] = self._void
        return d

    def __eq__(self, other: Interruption) -> bool:
        # We can't rely on UIDs here, as those are auto-generated
        return (self._reason == other._reason
                and self._create_date == other._create_date
                and self._duration == other._duration)

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
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from fk.core.abstract_cryptograph import AbstractCryptograph
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy

T = TypeVar('T')
TRoot = TypeVar('TRoot')


class AbstractSerializer(ABC, Generic[T, TRoot]):
    _settings: AbstractSettings
    _cryptograph: AbstractCryptograph

    def __init__(self, settings: AbstractSettings, cryptograph: AbstractCryptograph):
        self._settings = settings
        self._cryptograph = cryptograph

    @abstractmethod
    def serialize(self, s: AbstractStrategy[TRoot]) -> T:
        pass

    @abstractmethod
    def deserialize(self, t: T) -> AbstractStrategy[TRoot] | None:
        pass

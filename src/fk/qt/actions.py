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
import json
from typing import Callable, Iterable, Self

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from fk.core.abstract_settings import AbstractSettings


class Actions:
    ALL: Self = None
    _window: QWidget
    _domains: dict[str, object]
    _actions: dict[str, QAction]
    _shortcuts: dict[str, str]
    _settings: AbstractSettings

    def __init__(self, window: QWidget, settings: AbstractSettings):
        self._window = window
        self._domains = dict()
        self._actions = dict()
        self._settings = settings
        self.update_from_settings()
        Actions.ALL = self

    def update_from_settings(self):
        self._shortcuts = json.loads(self._settings.get('Application.shortcuts'))
        for a in self._actions.keys():
            if a in self._shortcuts:
                self._actions[a].setShortcut(self._shortcuts[a])

    def add(self,
            name: str,
            text: str,
            shortcut: str,
            icon: str | None,
            member: Callable,
            is_toggle: bool = False,
            is_checked: bool = False) -> QAction:
        res: QAction = QAction(text, self._window)
        res.setObjectName(name)
        if shortcut is not None:
            if name in self._shortcuts:
                res.setShortcut(self._shortcuts[name])
            else:
                res.setShortcut(shortcut)
        if icon is not None:
            res.setIcon(QIcon(icon))
        if is_toggle:
            res.setCheckable(True)
            res.setChecked(is_checked)
            res.toggled.connect(lambda checked: self._call(name, member, checked))
        else:
            res.triggered.connect(lambda: self._call(name, member))
        self._window.addAction(res)
        self._actions[name] = res
        return res

    def _call(self, name: str, member: Callable, checked: bool = None):
        [domain, _] = name.split('.')
        if domain in self._domains:
            if checked is None:
                member(self._domains[domain])
            else:
                member(self._domains[domain], checked)
        else:
            raise Exception(f'Attempt to call unbound action {name}')

    def bind(self, domain: str, obj: object):
        self._domains[domain] = obj

    def all(self) -> list[QAction]:
        return list(self._actions.values())

    def __getitem__(self, name: str) -> QAction:
        return self._actions[name]

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    def __iter__(self) -> Iterable[str]:
        return (x for x in self._actions)

    def __len__(self) -> int:
        return len(self._actions)

    def values(self) -> Iterable[QAction]:
        return self._actions.values()

    def keys(self) -> Iterable[str]:
        return self._actions.keys()

    def get_settings(self):
        return self._settings

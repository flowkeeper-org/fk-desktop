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

import json
from typing import Callable, Iterable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from fk.core.abstract_settings import AbstractSettings


class Actions:
    ALL: Actions = None
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
                action = self._actions[a]
                action.setShortcut(self._shortcuts[a])
                action.setToolTip(f"{action.text()} ({self._shortcuts[a]})")

    def add(self,
            name: str,
            text: str,
            shortcut: str | None,
            icon: str | None,
            member: Callable,
            is_toggle: bool = False,
            is_checked: bool = False) -> QAction:
        res: QAction = QAction(text, self._window)
        res.setObjectName(name)
        if shortcut is None:
            res.setToolTip(text)
        else:
            if name in self._shortcuts:
                res.setShortcut(self._shortcuts[name])
                res.setToolTip(f"{text} ({self._shortcuts[name]})")
            else:
                res.setShortcut(shortcut)
                res.setToolTip(f"{text} ({shortcut})")
        if icon is not None:
            # res.setIcon(QIcon(icon))
            if type(icon) is str:
                res.setIcon(QIcon.fromTheme(icon))
            else:
                qi = QIcon()
                qi.addPixmap(QIcon.fromTheme(icon[0]).pixmap(48),
                             QIcon.Mode.Normal,
                             QIcon.State.On)
                qi.addPixmap(QIcon.fromTheme(icon[1]).pixmap(48),
                             QIcon.Mode.Normal,
                             QIcon.State.Off)
                res.setIcon(qi)
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

    def all_actions_defined(self) -> None:
        if self._settings.get('Application.shortcuts') == '{}':
            shortcuts = dict()
            for a in self._actions:
                shortcuts[a] = self._actions[a].shortcut().toString()
            self._settings.set({'Application.shortcuts': json.dumps(shortcuts)})

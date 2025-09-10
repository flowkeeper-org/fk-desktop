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
from typing import Type

from PySide6.QtCore import QRect
from PySide6.QtGui import QIcon, Qt, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QMainWindow, QSystemTrayIcon, QMenu

from fk.core.abstract_event_source import start_workitem
from fk.core.abstract_timer_display import AbstractTimerDisplay
from fk.core.event_source_holder import EventSourceHolder
from fk.core.pomodoro import Pomodoro
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.qt.actions import Actions
from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer


class TrayIcon(QSystemTrayIcon, AbstractTimerDisplay):
    _about_window: QMainWindow
    _default_icon: QIcon
    _next_icon: QIcon
    _actions: Actions
    _timer_renderer: AbstractTimerRenderer | None
    _continue_workitem: Workitem | None
    _size: int

    def __init__(self,
                 parent: QWidget,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 actions: Actions,
                 size: int,
                 cls: Type[AbstractTimerRenderer],
                 is_dark: bool):
        super().__init__(parent, timer=timer, source_holder=source_holder)
        self._size = size
        self._default_icon = QIcon(":/flowkeeper.png")
        if is_dark:
            # We don't use QIcon.fromTheme() here because we can't predict the tray background color
            self._next_icon = QIcon(':/icons/dark/24x24/tool-next.svg')
        else:
            self._next_icon = QIcon(':/icons/light/24x24/tool-next.svg')
        self._actions = actions
        self._continue_workitem = None
        self.setObjectName('tray')
        self._timer_renderer = cls(None,
                                   QColor('#000000' if is_dark else '#ffffff'),
                                   QColor('#ffffff' if is_dark else '#000000'),
                                   False,
                                   True)
        self._timer_renderer.setObjectName('TrayIconRenderer')

        self.activated.connect(lambda reason:
                               self._tray_clicked() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)

        self._initialize_menu()
        self.reset()

    def _initialize_menu(self):
        menu = QMenu()
        if 'focus.voidPomodoro' in self._actions:
            menu.addAction(self._actions['focus.voidPomodoro'])
        if 'focus.finishTracking' in self._actions:
            menu.addAction(self._actions['focus.finishTracking'])
        menu.addSeparator()
        if 'window.showMainWindow' in self._actions:
            menu.addAction(self._actions['window.showMainWindow'])
        if 'application.settings' in self._actions:
            menu.addAction(self._actions['application.settings'])
        # if 'window.quickConfig' in self._actions:
        #     menu.addAction(self._actions['window.quickConfig'])
        if 'application.quit' in self._actions:
            menu.addAction(self._actions['application.quit'])
        self.setContextMenu(menu)

    def kill(self):
        super().kill()
        pass    # Unsubscribe any externals here

    def reset(self):
        self.setToolTip("It's time for the next Pomodoro.")
        if self._timer_renderer.has_idle_display():
            self._timer_renderer.set_values(0, 1, None, None, 'idle')
            self.paint()
        else:
            self.setIcon(self._default_icon)

    def _tray_clicked(self) -> None:
        if self._continue_workitem is not None and self._continue_workitem.is_startable() and self.timer.is_idling():
            if self._continue_workitem is None:
                raise Exception('Cannot start next pomodoro on non-existent work item')
            start_workitem(self._continue_workitem, self._source_holder.get_source())
        else:
            if 'window.showMainWindow' in self._actions:
                self._actions['window.showMainWindow'].trigger()

    def paint(self) -> None:
        tray_width = 48 if self._size is None else self._size
        tray_height = 48 if self._size is None else self._size
        pixmap = QPixmap(tray_width, tray_height)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self._timer_renderer.repaint(painter, QRect(0, 0, tray_width, tray_height))
        self.setIcon(pixmap)

    def tick(self, pomodoro: Pomodoro, state_text: str, my_value: float, my_max: float, mode: str) -> None:
        self.setToolTip(f"{state_text} ({pomodoro.get_parent().get_name()})")
        self._timer_renderer.set_values(my_value, my_max, None, None, mode)
        self.paint()

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        if new_mode == 'undefined' or new_mode == 'idle':
            self.reset()
            if old_mode == 'working' or old_mode == 'resting' or old_mode == 'long-resting':
                self.showMessage("Ready", "It's time for the next Pomodoro.", self._default_icon)
        elif new_mode == 'resting' and old_mode == 'working':
            self.showMessage("Work is done", "Have some rest", self._default_icon)
        elif new_mode == 'long-resting' and old_mode == 'working':
            self.showMessage("A series is done", "Enjoy a long rest", self._default_icon)
        elif new_mode == 'ready':
            if self._continue_workitem is not None:
                self.setToolTip(f'Continue? ({self._continue_workitem.get_name()})')
            self.showMessage("Ready", "Continue?", self._next_icon)
            self._timer_renderer.set_values(0, 1, None, None, 'ready')
            if self._timer_renderer.has_next_display():
                self.paint()
            else:
                self.setIcon(self._next_icon)

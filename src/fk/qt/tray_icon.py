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
from PySide6.QtCore import QRect
from PySide6.QtGui import QIcon, Qt, QPixmap, QPainter
from PySide6.QtWidgets import QWidget, QMainWindow, QSystemTrayIcon, QMenu

from fk.core.abstract_timer_display import AbstractTimerDisplay
from fk.core.event_source_holder import EventSourceHolder
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import StartWorkStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.qt.actions import Actions
from fk.qt.timer_renderer import TimerRenderer


class TrayIcon(QSystemTrayIcon, AbstractTimerDisplay):
    _about_window: QMainWindow
    _default_icon: QIcon
    _next_icon: QIcon
    _actions: Actions
    _timer_widget: TimerRenderer | None
    _continue_workitem: Workitem | None

    def __init__(self,
                 parent: QWidget,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent, timer=timer, source_holder=source_holder)

        self._default_icon = QIcon(":/icons/logo8.png")
        self._next_icon = QIcon.fromTheme('tool-next')
        self._actions = actions
        self._continue_workitem = None
        self._timer_widget = TimerRenderer(
            None,
            None,
            None,
            0.05,
            0.5,
            None,
            None,
            2,
            0,
            120,
        )

        self.activated.connect(lambda reason:
                               self._tray_clicked() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)

        self._initialize_menu()
        self.reset()

    def _initialize_menu(self):
        menu = QMenu()
        if 'focus.voidPomodoro' in self._actions:
            menu.addAction(self._actions['focus.voidPomodoro'])
        menu.addSeparator()
        if 'window.showMainWindow' in self._actions:
            menu.addAction(self._actions['window.showMainWindow'])
        if 'application.settings' in self._actions:
            menu.addAction(self._actions['application.settings'])
        if 'application.quit' in self._actions:
            menu.addAction(self._actions['application.quit'])
        self.setContextMenu(menu)

    def reset(self):
        self.setToolTip("It's time for the next Pomodoro.")
        self.setIcon(self._default_icon)

    def _tray_clicked(self) -> None:
        if self._continue_workitem is not None and self._continue_workitem.is_startable() and self._timer.is_idling():
            settings = self._source_holder.get_settings()
            self._source_holder.get_source().execute(StartWorkStrategy, [
                self._continue_workitem.get_uid(),
                settings.get('Pomodoro.default_work_duration'),
                settings.get('Pomodoro.default_rest_duration'),
            ])
        else:
            if self.parent().isHidden():
                self.parent().show()
            else:
                self.parent().hide()

    def _paint_timer(self) -> None:
        tray_width = 48
        tray_height = 48
        pixmap = QPixmap(tray_width, tray_height)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self._timer_widget.repaint(painter, QRect(0, 0, tray_width, tray_height))
        self.setIcon(pixmap)

    def tick(self, pomodoro: Pomodoro, state_text: str, completion: float) -> None:
        self.setToolTip(f"{state_text} ({pomodoro.get_parent().get_name()})")
        self._timer_widget.set_values(completion, self._timer.is_working())
        self._paint_timer()

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        if new_mode == 'undefined' or new_mode == 'idle':
            self.reset()
            if old_mode == 'working' or old_mode == 'resting':
                self.showMessage("Ready", "It's time for the next Pomodoro.", self._default_icon)
        elif new_mode == 'resting' and old_mode == 'working':
            self.showMessage("Work is done", "Have some rest", self._default_icon)
        elif new_mode == 'ready':
            self.setToolTip(f'Start another Pomodoro? ({self._continue_workitem.get_name()})')
            self.showMessage("Ready", "Start another pomodoro?", self._next_icon)
            self.setIcon(self._next_icon)

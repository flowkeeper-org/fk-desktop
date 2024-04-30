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

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemComplete, SourceMessagesProcessed
from fk.core.pomodoro_strategies import StartWorkStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.qt.actions import Actions
from fk.qt.timer_widget import TimerWidget, render_for_pixmap


class TrayIcon(QSystemTrayIcon):
    _about_window: QMainWindow
    _default_icon: QIcon
    _next_icon: QIcon
    _actions: Actions
    _source_holder: EventSourceHolder
    _timer_widget: TimerWidget | None
    _timer: PomodoroTimer

    # TODO: Set it correctly in some event handler (finish pomodoro?)
    _continue_workitem: Workitem | None

    def __init__(self,
                 parent: QWidget,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 actions: Actions):
        super().__init__(parent)

        self._default_icon = QIcon(":/icons/logo.png")
        self._next_icon = QIcon("tool-next")
        self._actions = actions
        self._source_holder = source_holder
        self._continue_workitem = None
        self._timer = timer
        self._timer_widget = render_for_pixmap()

        source_holder.on(AfterSourceChanged, self._on_source_changed)
        timer.on("Timer*", self._update)
        timer.on("Timer*Complete", self._show_notification)

        self.activated.connect(self._on_activated)
        menu = QMenu()
        if 'focus.voidPomodoro' in actions:
            menu.addAction(actions['focus.voidPomodoro'])
        menu.addSeparator()
        if 'window.showMainWindow' in actions:
            menu.addAction(actions['window.showMainWindow'])
        if 'application.settings' in actions:
            menu.addAction(actions['application.settings'])
        if 'application.quit' in actions:
            menu.addAction(actions['application.quit'])
        self.setContextMenu(menu)

        self._update()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            return self._tray_clicked()

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        self.setToolTip("It's time for the next Pomodoro.")
        self.reset()
        source.on(AfterWorkitemComplete, self.reset)
        source.on(AfterWorkitemComplete, self._update)
        source.on(SourceMessagesProcessed, self._update)

    def reset(self, event: str = None, **kwargs):
        self.setIcon(self._default_icon)

    def _tray_clicked(self) -> None:
        if self._continue_workitem is not None:
            self._source_holder.get_source().execute(StartWorkStrategy, [
                self._continue_workitem.get_uid(),
                self._source_holder.get_settings().get('Pomodoro.default_work_duration')
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

    def _update(self, event: str = None, **kwargs) -> None:
        running_workitem: Workitem = self._timer.get_running_workitem()
        if self._timer.is_idling():
            w = kwargs.get('workitem')  # != running_workitem for end-of-pomodoro
            if w is not None and w.is_startable():
                self.setToolTip(f'Start another Pomodoro? ({w.get_name()})')
            else:
                self.setToolTip("It's time for the next Pomodoro.")
            self.reset()
        elif self._timer.is_working() or self._timer.is_resting():
            remaining_duration = self._timer.get_remaining_duration()     # This is always >= 0
            remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
            remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
            state = 'Focus' if self._timer.is_working() else 'Rest'
            txt = f'{state}: {remaining_minutes}:{remaining_seconds}'
            self.setToolTip(f"{txt} left ({running_workitem.get_name()})")
            self._timer_widget.set_values(
                remaining_duration / self._timer.get_planned_duration(),
                None,
                ""  # f'{remaining_minutes}:{remaining_seconds}'
            )
            self._paint_timer()
        elif self._timer.is_initializing():
            print('The timer is still initializing')
            self.reset()
        else:
            raise Exception("The timer is in an unexpected state")

    def _show_notification(self, event: str, **kwargs) -> None:
        if event == 'TimerWorkComplete':
            self.showMessage("Work is done", "Have some rest", self._default_icon)
        elif event == 'TimerRestComplete':
            icon = self._default_icon
            w = kwargs.get('workitem')
            if w is not None and w.is_startable():
                icon = self._next_icon
            self.showMessage("Ready", "Start a new pomodoro", icon)

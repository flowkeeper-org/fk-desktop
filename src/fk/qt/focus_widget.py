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
from typing import Callable

from PySide6.QtCore import QSize, QPoint
from PySide6.QtGui import QIcon, QFont, QAction, QPainter, QPixmap, Qt, QColor, QGradient
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QToolButton, \
    QMessageBox, QMenu

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.events import AfterWorkitemComplete, AfterSettingChanged
from fk.core.pomodoro_strategies import CompletePomodoroStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.desktop.application import Application, AfterFontsChanged
from fk.qt.timer_widget import render_for_widget, TimerWidget


class FocusWidget(QWidget):
    _source: AbstractEventSource
    _settings: AbstractSettings
    _timer: PomodoroTimer
    _header_text: QLabel
    _header_subtext: QLabel
    _timer_display: TimerWidget
    _actions: dict[str, QAction]
    _buttons: dict[str, QToolButton]
    _application: Application
    _pixmap: QPixmap | None

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 timer: PomodoroTimer,
                 source: AbstractEventSource,
                 settings: AbstractSettings,
                 actions: dict[str, QAction]):
        super().__init__(parent)
        self._source = source
        self._settings = settings
        self._timer = timer
        self._actions = actions
        self._application = application
        self._buttons = dict()
        self._pixmap = None

        self.setObjectName('focus')
        sp1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sp1.setHorizontalStretch(0)
        sp1.setVerticalStretch(0)
        self.setSizePolicy(sp1)
        self.setMinimumHeight(80)
        self.setMinimumWidth(0)
        self.setMaximumHeight(16777215)
        self.setMaximumWidth(16777215)

        layout = QHBoxLayout()
        layout.setObjectName("focus_layout")
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(0)
        self.setLayout(layout)

        text_layout = QVBoxLayout()
        text_layout.setObjectName("text_layout")
        # Here
        layout.addLayout(text_layout)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)

        header_text = QLabel(self)
        header_text.setObjectName('headerText')
        text_layout.addWidget(header_text)
        sp2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sp2.setHorizontalStretch(0)
        sp2.setVerticalStretch(0)
        header_text.setSizePolicy(sp2)
        header_text.setText("Idle")
        header_text.setFont(application.get_header_font())
        application.on(AfterFontsChanged, lambda header_font, **kwargs: header_text.setFont(header_font))
        self._header_text = header_text

        header_subtext = QLabel(self)
        header_subtext.setObjectName('headerSubtext')
        text_layout.addWidget(header_subtext)
        header_subtext.setText("Welcome to Flowkeeper!")
        self._header_subtext = header_subtext

        outer_timer_widget = QWidget(self)
        outer_timer_widget.setObjectName("timer")
        layout.addWidget(outer_timer_widget)
        sp3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sp3.setHorizontalStretch(0)
        sp3.setVerticalStretch(0)
        outer_timer_widget.setSizePolicy(sp3)
        outer_timer_widget.setMinimumHeight(60)
        outer_timer_widget.setMinimumWidth(60)
        outer_timer_widget.setMaximumHeight(60)
        outer_timer_widget.setMaximumWidth(60)
        outer_timer_widget.setBaseSize(QSize(0, 0))

        inner_timer_layout = QHBoxLayout(outer_timer_widget)
        inner_timer_layout.setObjectName("inner_timer_layout")
        inner_timer_layout.setContentsMargins(0, 0, 0, 0)
        inner_timer_layout.setSpacing(0)
        inner_timer_layout.addWidget(
            self._create_button("toolVoid",
                                "actionVoid",
                                "Void Pomodoro",
                                "Ctrl+V",
                                self.void_pomodoro,
                                ":/icons/tool-void.svg",
                                parent=outer_timer_widget))
        layout.addWidget(
            self._create_button("toolNext",
                                "startItem",
                                "",
                                "",
                                None,
                                ":/icons/tool-next.svg"))
        layout.addWidget(
            self._create_button("toolComplete",
                                "completeItem",
                                "",
                                "",
                                None,
                                ":/icons/tool-complete.svg"))
        layout.addWidget(
            self._create_button("toolFilter",
                                "",
                                "",
                                "",
                                self._display_filter,
                                ":/icons/tool-filter.svg"))
        layout.addWidget(
            self._create_button("toolShowAll",
                                "showAll",
                                "",
                                "",
                                None,
                                ":/icons/tool-show-all.svg"))
        layout.addWidget(
            self._create_button("toolShowTimerOnly",
                                "showTimerOnly",
                                "",
                                "",
                                None,
                                ":/icons/tool-show-timer-only.svg"))

        self._buttons['toolNext'].hide()
        self._buttons['toolComplete'].hide()
        self._buttons['toolShowAll'].hide()

        self._timer_display = render_for_widget(
            parent.palette(),
            outer_timer_widget,
            QFont(),
            0.3
        )

        self.update_header()

        source.on(AfterWorkitemComplete, lambda event, workitem, **kwargs: self.update_header(workitem=workitem))
        timer.on('Timer*', lambda **kwargs: self.update_header())

        self.eye_candy()
        settings.on(AfterSettingChanged, self._on_setting_changed)

    def _create_button(self,
                       name: str,
                       action: str,
                       txt: str,
                       shortcut: str,
                       callback: Callable | None,
                       icon: str,
                       parent: QWidget = None):
        btn = QToolButton(self if parent is None else parent)
        btn.setObjectName(name)
        btn.setIcon(QIcon(icon))
        btn.setIconSize(QSize(32, 32))
        if action:
            if action not in self._actions:
                a = QAction(txt, self)
                a.triggered.connect(callback)
                a.setShortcut(shortcut)
                a.setIcon(QIcon(icon))
                self._actions[action] = a
            btn.setDefaultAction(self._actions[action])
        else:
            btn.clicked.connect(callback)
        self._buttons[name] = btn
        return btn

    def _display_filter(self):
        menu_filter = QMenu("Filter", self.parent())
        menu_filter.addAction(self._actions['showCompleted'])
        menu_filter.exec(
            self.parent().mapToGlobal(
                self._buttons['toolFilter'].geometry().center()))

    def update_header(self, **kwargs) -> None:
        running_workitem: Workitem = self._timer.get_running_workitem()
        if self._timer.is_idling():
            w = kwargs.get('workitem')  # != running_workitem for end-of-pomodoro
            if w is not None and w.is_startable():
                self._header_text.setText('Start another Pomodoro?')
                self._header_subtext.setText(w.get_name())
            else:
                self._header_text.setText('Idle')
                self._header_subtext.setText("It's time for the next Pomodoro.")
            self._buttons['toolVoid'].hide()
            self._timer_display.set_values(0, None, "")
            self._timer_display.hide()
        elif self._timer.is_working() or self._timer.is_resting():
            remaining_duration = self._timer.get_remaining_duration()  # This is always >= 0
            remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
            remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
            state = 'Focus' if self._timer.is_working() else 'Rest'
            txt = f'{state}: {remaining_minutes}:{remaining_seconds}'
            self._header_text.setText(f'{txt} left')
            self._header_subtext.setText(running_workitem.get_name())
            self._buttons['toolVoid'].show()
            self._buttons['toolNext'].hide()
            self._buttons['toolComplete'].hide()
            self._timer_display.set_values(
                remaining_duration / self._timer.get_planned_duration(),
                None,
                ""  # f'{remaining_minutes}:{remaining_seconds}'
            )
            self._timer_display.show()
        else:
            raise Exception("The timer is in an unexpected state")
        self._timer_display.repaint()

    def eye_candy(self):
        eyecandy_type = self._settings.get('Application.eyecandy_type')
        if eyecandy_type == 'image':
            header_bg = self._settings.get('Application.eyecandy_image')
            if header_bg:
                header_bg = self._settings.get('Application.eyecandy_image')
                self._pixmap = QPixmap(header_bg)
            else:
                self._pixmap = None
        self.repaint()

    def paintEvent(self, event):
        super().paintEvent(event)
        eyecandy_type = self._settings.get('Application.eyecandy_type')
        if eyecandy_type == 'image':
            if self._pixmap is not None:
                img = self._pixmap
                painter = QPainter(self)
                painter.drawPixmap(
                    QPoint(0, 0),
                    img.scaled(
                        QSize(self.width(), self.width() * img.height() / img.width()),
                        mode=Qt.TransformationMode.SmoothTransformation))
        elif eyecandy_type == 'gradient':
            painter = QPainter(self)
            gradient = self._settings.get('Application.eyecandy_gradient')
            painter.fillRect(self.rect(), QGradient.Preset[gradient])

    def _on_setting_changed(self, event: str, name: str, old_value: str, new_value: str):
        if name.startswith('Application.eyecandy'):
            self.eye_candy()

    def void_pomodoro(self) -> None:
        for backlog in self._source.backlogs():
            workitem, _ = backlog.get_running_workitem()
            if workitem is not None:
                if QMessageBox().warning(self.parent(),
                                         "Confirmation",
                                         f"Are you sure you want to void current pomodoro?",
                                         QMessageBox.StandardButton.Ok,
                                         QMessageBox.StandardButton.Cancel
                                         ) == QMessageBox.StandardButton.Ok:
                    self._source.execute(CompletePomodoroStrategy, [workitem.get_uid(), "canceled"])

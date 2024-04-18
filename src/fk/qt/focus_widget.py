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
import traceback

from PySide6.QtCore import QSize, QPoint
from PySide6.QtGui import QIcon, QFont, QPainter, QPixmap, Qt, QGradient, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QToolButton, \
    QMessageBox, QMenu

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterWorkitemComplete, AfterSettingsChanged
from fk.core.pomodoro_strategies import VoidPomodoroStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.desktop.application import Application, AfterFontsChanged
from fk.qt.actions import Actions
from fk.qt.timer_widget import render_for_widget, TimerWidget


class FocusWidget(QWidget):
    _source_holder: EventSourceHolder
    _settings: AbstractSettings
    _timer: PomodoroTimer
    _header_text: QLabel
    _header_subtext: QLabel
    _timer_display: TimerWidget
    _actions: Actions
    _buttons: dict[str, QToolButton]
    _application: Application
    _pixmap: QPixmap | None

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings,
                 actions: Actions):
        super().__init__(parent)
        self._source_holder = source_holder
        self._settings = settings
        self._timer = timer
        self._actions = actions
        self._application = application
        self._buttons = dict()
        self._pixmap = None

        self.setObjectName('focus')

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

        inner_timer_layout.addWidget(self._create_button("focus.voidPomodoro"))
        layout.addWidget(self._create_button("focus.nextPomodoro"))
        layout.addWidget(self._create_button("focus.completeItem"))
        layout.addWidget(self._create_button("focus.showFilter"))

        if "window.showAll" in actions:
            layout.addWidget(self._create_button("window.showAll"))
            self._buttons['window.showAll'].hide()
        if "window.showFocus" in actions:
            layout.addWidget(self._create_button("window.showFocus"))

        self._buttons['focus.nextPomodoro'].hide()
        self._buttons['focus.completeItem'].hide()

        self._timer_display = render_for_widget(
            parent.palette(),
            outer_timer_widget,
            QFont(),
            0.3
        )

        self.update_header()

        # Last because we rely on PomodoroTimer to update the header, and want it to update its state first
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        timer.on('Timer*', lambda **kwargs: self.update_header())

        self.eye_candy()
        settings.on(AfterSettingsChanged, self._on_setting_changed)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        source.on(AfterWorkitemComplete, lambda event, workitem, **kwargs: self.update_header(workitem=workitem))
        self._reset_header()

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('focus.voidPomodoro', "Void Pomodoro", 'Ctrl+V', ":/icons/tool-void.svg", FocusWidget._void_pomodoro)
        actions.add('focus.nextPomodoro', "Next Pomodoro", None, ":/icons/tool-next.svg", FocusWidget._next_pomodoro)
        actions.add('focus.completeItem', "Complete Item", None, ":/icons/tool-complete.svg", FocusWidget._complete_item)
        actions.add('focus.showFilter', "Show Filter", None, ":/icons/tool-filter.svg", FocusWidget._display_filter)

    def _create_button(self,
                       name: str,
                       parent: QWidget = None):
        action = self._actions[name]
        btn = QToolButton(self if parent is None else parent)
        btn.setObjectName(name)
        btn.setIcon(QIcon(action.icon()))
        btn.setIconSize(QSize(32, 32))
        btn.setDefaultAction(action)
        self._buttons[name] = btn
        return btn

    def _display_filter(self):
        if 'workitems_table.showCompleted' not in self._actions:
            raise Exception('Show Completed action is undefined')
        menu_filter = QMenu("Filter", self.parent())
        menu_filter.addAction(self._actions['workitems_table.showCompleted'])
        menu_filter.exec(
            self.parent().mapToGlobal(
                self._buttons['focus.showFilter'].geometry().center()))

    def _reset_header(self, text: str = 'Idle', subtext: str = "It's time for the next Pomodoro.") -> None:
        self._header_text.setText(text)
        self._header_subtext.setText(subtext)
        self._buttons['focus.voidPomodoro'].hide()
        self._actions['focus.voidPomodoro'].setDisabled(True)
        self._timer_display.reset()
        self._timer_display.hide()
        self._timer_display.repaint()

    def update_header(self, **kwargs) -> None:
        if self._timer.is_idling():
            w = kwargs.get('workitem')  # != running_workitem for end-of-pomodoro
            if w is not None and w.is_startable():
                self._reset_header('Start another Pomodoro?', w.get_name())
            else:
                self._reset_header()
        elif self._timer.is_working() or self._timer.is_resting():
            remaining_duration = self._timer.get_remaining_duration()  # This is always >= 0
            remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
            remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
            state = 'Focus' if self._timer.is_working() else 'Rest'
            txt = f'{state}: {remaining_minutes}:{remaining_seconds}'
            self._header_text.setText(f'{txt} left')
            self._header_subtext.setText(self._timer.get_running_workitem().get_name())
            self._buttons['focus.voidPomodoro'].show()
            self._actions['focus.voidPomodoro'].setDisabled(False)
            self._buttons['focus.nextPomodoro'].hide()
            self._buttons['focus.completeItem'].hide()
            self._timer_display.set_values(
                remaining_duration / self._timer.get_planned_duration(),
                None,
                ""  # f'{remaining_minutes}:{remaining_seconds}'
            )
            self._timer_display.show()
            self._timer_display.repaint()
        elif self._timer.is_initializing():
            print('The timer is still initializing')
        else:
            raise Exception("The timer is in an unexpected state")

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
            try:
                painter.fillRect(self.rect(), QGradient.Preset[gradient])
            except Exception as e:
                print('ERROR while updating the gradient -- ignoring it', e)
                print("\n".join(traceback.format_exception(e)))
                painter.fillRect(self.rect(), QColor.setRgb(127, 127, 127))

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        for name in new_values.keys():
            if name.startswith('Application.eyecandy'):
                self.eye_candy()
                return

    def _void_pomodoro(self) -> None:
        for backlog in self._source_holder.get_source().backlogs():
            workitem, _ = backlog.get_running_workitem()
            if workitem is not None:
                if QMessageBox().warning(self.parent(),
                                         "Confirmation",
                                         f"Are you sure you want to void current pomodoro?",
                                         QMessageBox.StandardButton.Ok,
                                         QMessageBox.StandardButton.Cancel
                                         ) == QMessageBox.StandardButton.Ok:
                    self._source_holder.get_source().execute(VoidPomodoroStrategy, [workitem.get_uid()])

    def _next_pomodoro(self) -> None:
        QMessageBox().warning(self.parent(),
                              "Not implemented",
                              f"Starting next pomodoro in the current item is not implemented",
                              QMessageBox.StandardButton.Ok)

    def _complete_item(self) -> None:
        QMessageBox().warning(self.parent(),
                              "Not implemented",
                              f"Completing current item is not implemented",
                              QMessageBox.StandardButton.Ok)

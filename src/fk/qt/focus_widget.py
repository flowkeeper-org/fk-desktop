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

from PySide6.QtCore import QSize, QPoint, QLine
from PySide6.QtGui import QIcon, QFont, QPainter, QPixmap, Qt, QGradient, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QToolButton, \
    QMessageBox, QMenu

from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterSettingsChanged
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import VoidPomodoroStrategy, StartWorkStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CompleteWorkitemStrategy
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
    _border_color: QColor
    _continue_workitem: Workitem | None

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
        self._continue_workitem = None

        self._border_color = QColor('#000000')
        self._set_border_color()

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
        self._buttons['focus.voidPomodoro'].hide()

        self._timer_display = render_for_widget(
            parent.palette(),
            outer_timer_widget,
            QFont(),
            0.3
        )

        timer.on(PomodoroTimer.TimerWorkStart, self._on_work_start)
        timer.on(PomodoroTimer.TimerWorkComplete, self._on_work_complete)
        timer.on(PomodoroTimer.TimerRestComplete, self._on_rest_complete)
        timer.on(PomodoroTimer.TimerTick, self._on_tick)
        timer.on(PomodoroTimer.TimerInitialized, self._on_timer_initialized)

        self.eye_candy()
        settings.on(AfterSettingsChanged, self._on_setting_changed)

    def _on_timer_initialized(self, event: str, timer: PomodoroTimer) -> None:
        if timer.is_resting() or timer.is_working():
            self._on_work_start()
        else:
            self._reset_header()

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('focus.voidPomodoro', "Void Pomodoro", 'Ctrl+V', "tool-void", FocusWidget._void_pomodoro)
        actions.add('focus.nextPomodoro', "Next Pomodoro", None, "tool-focus-next", FocusWidget._next_pomodoro)
        actions.add('focus.completeItem', "Complete Item", None, "tool-focus-complete", FocusWidget._complete_item)
        actions.add('focus.showFilter', "Show Filter", None, "tool-filter", FocusWidget._display_filter)

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
        self._buttons['focus.completeItem'].hide()
        self._buttons['focus.voidPomodoro'].hide()
        self._actions['focus.voidPomodoro'].setDisabled(True)
        self._timer_display.reset()
        self._timer_display.hide()
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
        rect = self.rect()
        painter = QPainter(self)
        eyecandy_type = self._settings.get('Application.eyecandy_type')
        if eyecandy_type == 'image':
            if self._pixmap is not None:
                img = self._pixmap
                painter.drawPixmap(
                    QPoint(0, 0),
                    img.scaled(
                        QSize(self.width(), self.width() * img.height() / img.width()),
                        mode=Qt.TransformationMode.SmoothTransformation))
        elif eyecandy_type == 'gradient':
            gradient = self._settings.get('Application.eyecandy_gradient')
            try:
                painter.fillRect(rect, QGradient.Preset[gradient])
            except Exception as e:
                print('ERROR while updating the gradient -- ignoring it', e)
                print("\n".join(traceback.format_exception(e)))
                painter.fillRect(self.rect(), QColor.setRgb(127, 127, 127))
        else:   # Default
            painter.setPen(self._border_color)
            painter.drawLine(QLine(rect.bottomLeft(), rect.bottomRight()))

    def _set_border_color(self):
        self._border_color = self._application.get_theme_variables(
            self._settings.get('Application.theme')
        ).get('FOCUS_BORDER_COLOR', '#000000')

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.theme' in new_values:
            self._set_border_color()
        if 'Application.eyecandy_type' in new_values or \
                'Application.eyecandy_gradient' in new_values or \
                'Application.eyecandy_image' in new_values:
            self.eye_candy()

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
        self._source_holder.get_source().execute(StartWorkStrategy, [
            self._continue_workitem.get_uid(),
            self._source_holder.get_settings().get('Pomodoro.default_work_duration'),
        ])

    def _complete_item(self) -> None:
        item = self._timer.get_running_workitem()
        if QMessageBox().warning(
                self,
                "Confirmation",
                f"Are you sure you want to complete workitem '{item.get_name()}'? This will void current pomodoro.",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Cancel
                ) == QMessageBox.StandardButton.Ok:
            self._source_holder.get_source().execute(CompleteWorkitemStrategy,
                                 [item.get_uid(), "finished"])

    def _on_tick(self, pomodoro: Pomodoro, **kwargs) -> None:
        state = 'Focus' if self._timer.is_working() else 'Rest'
        txt = f'{state}: {self._timer.format_remaining_duration()}'
        self._header_text.setText(f'{txt} left')

        self._timer_display.set_values(
            self._timer.get_completion(),
            None,
            ""
        )
        self._timer_display.repaint()

    def _on_work_start(self, **kwargs) -> None:
        item = self._timer.get_running_workitem()
        self._continue_workitem = item
        self._header_subtext.setText(item.get_name())
        self._timer_display.show()
        self._on_tick(self._timer.get_running_pomodoro())
        self._buttons['focus.voidPomodoro'].show()
        self._actions['focus.voidPomodoro'].setDisabled(False)
        self._buttons['focus.nextPomodoro'].hide()
        self._buttons['focus.completeItem'].show()

    def _on_work_complete(self, **kwargs) -> None:
        self._on_tick(self._timer.get_running_pomodoro())

    def _on_rest_complete(self, workitem: Workitem, **kwargs) -> None:
        if workitem.is_startable():
            self._reset_header('Start another Pomodoro?', workitem.get_name())
            self._buttons['focus.nextPomodoro'].show()
        else:
            self._reset_header()
            self._buttons['focus.nextPomodoro'].hide()

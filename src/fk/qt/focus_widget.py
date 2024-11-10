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
import logging

from PySide6.QtCore import QSize, QPoint, QLine
from PySide6.QtGui import QIcon, QPainter, QPixmap, Qt, QGradient, QColor, QMouseEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QToolButton, \
    QMessageBox, QMenu, QSizePolicy

from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer_display import AbstractTimerDisplay
from fk.core.event_source_holder import EventSourceHolder
from fk.core.events import AfterSettingsChanged
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import VoidPomodoroStrategy, StartWorkStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CompleteWorkitemStrategy
from fk.desktop.application import Application, AfterFontsChanged
from fk.qt.actions import Actions
from fk.qt.timer_widget import TimerWidget

logger = logging.getLogger(__name__)
DISPLAY_HEIGHT = 80


class FocusWidget(QWidget, AbstractTimerDisplay):
    _settings: AbstractSettings
    _header_text: QLabel
    _header_subtext: QLabel
    _actions: Actions
    _buttons: dict[str, QToolButton]
    _application: Application
    _pixmap: QPixmap | None
    _border_color: QColor
    _continue_workitem: Workitem | None
    _timer_widget: TimerWidget
    _moving_around: QPoint | None

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings,
                 actions: Actions):
        super().__init__(parent, timer=timer, source_holder=source_holder)

        self._apply_size_policy()

        self._settings = settings
        self._actions = actions
        self._application = application
        self._buttons = dict()
        self._pixmap = None
        self._continue_workitem = None
        self._moving_around = None

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
        layout.addLayout(text_layout)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.addStretch()

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

        text_layout.addStretch()

        self._timer_widget = TimerWidget(self,
                                         'timer',
                                         self._create_button("focus.voidPomodoro"))
        layout.addWidget(self._timer_widget)
        layout.addWidget(self._create_button("focus.nextPomodoro"))
        layout.addWidget(self._create_button("focus.completeItem"))
        layout.addWidget(self._create_button("focus.showFilter"))

        if "window.showAll" in actions:
            layout.addWidget(self._create_button("window.showAll"))
            self._buttons['window.showAll'].hide()
        if "window.showFocus" in actions:
            layout.addWidget(self._create_button("window.showFocus"))
        if "window.pinWindow" in actions:
            layout.addWidget(self._create_button("window.pinWindow"))
            layout.addWidget(self._create_button("window.unpinWindow"))
            self._update_pinned_button(settings.get('Application.always_on_top') == 'True')

        self._buttons['focus.nextPomodoro'].hide()
        self._buttons['focus.completeItem'].hide()
        self._buttons['focus.voidPomodoro'].hide()

        self.eye_candy()
        settings.on(AfterSettingsChanged, self._on_setting_changed)

    def update_fonts(self):
        self._header_text.setFont(self._application.get_header_font())

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

    def reset(self, text: str = 'Idle', subtext: str = "It's time for the next Pomodoro.") -> None:
        self._header_text.setText(text)
        self._header_subtext.setText(subtext)
        self._buttons['focus.completeItem'].hide()
        self._buttons['focus.voidPomodoro'].hide()
        self._actions['focus.voidPomodoro'].setDisabled(True)
        self._timer_widget.reset()

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
                logger.error(f'ERROR while updating the gradient to {gradient} -- ignoring it', exc_info=e)
                painter.fillRect(self.rect(), QColor.setRgb(127, 127, 127))
        else:   # Default
            painter.setPen(self._border_color)
            painter.drawLine(QLine(rect.bottomLeft(), rect.bottomRight()))

    def _set_border_color(self):
        self._border_color = self._application.get_theme_variables()['FOCUS_BORDER_COLOR']

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.theme' in new_values:
            self._set_border_color()
        if 'Application.eyecandy_type' in new_values or \
                'Application.eyecandy_gradient' in new_values or \
                'Application.eyecandy_image' in new_values:
            self.eye_candy()
        if 'Application.always_on_top' in new_values:
            self._update_pinned_button(new_values['Application.always_on_top'] == 'True')

    def _update_pinned_button(self, pinned: bool):
        self._buttons['window.pinWindow'].setVisible(not pinned)
        self._buttons['window.unpinWindow'].setVisible(pinned)

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
        settings = self._source_holder.get_settings()
        self._source_holder.get_source().execute(StartWorkStrategy, [
            self._continue_workitem.get_uid(),
            settings.get('Pomodoro.default_work_duration'),
            settings.get('Pomodoro.default_rest_duration'),
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

    def tick(self, pomodoro: Pomodoro, state_txt: str, completion: float) -> None:
        self._header_text.setText(state_txt)
        self._timer_widget.set_values(completion)

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        if new_mode == 'undefined' or new_mode == 'idle':
            self.reset()
            self._buttons['focus.nextPomodoro'].hide()
        elif new_mode == 'working' or new_mode == 'resting':
            self._header_subtext.setText(self._timer.get_running_workitem().get_name())
            self._actions['focus.voidPomodoro'].setDisabled(False)
            self._buttons['focus.voidPomodoro'].show()
            self._buttons['focus.nextPomodoro'].hide()
            self._buttons['focus.completeItem'].show()
        elif new_mode == 'ready':
            self.reset('Start another Pomodoro?', self._continue_workitem.get_name())
            self._buttons['focus.nextPomodoro'].show()

    def _apply_size_policy(self):
        sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp.setVerticalStretch(0)
        self.setSizePolicy(sp)
        self.setMinimumHeight(DISPLAY_HEIGHT)
        self.setMaximumHeight(DISPLAY_HEIGHT)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._moving_around = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._moving_around is not None:
            self.window().move(self.window().pos() + event.pos() - self._moving_around)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._moving_around = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        show_all = self._buttons['window.showAll']
        show_focus = self._buttons['window.showFocus']
        if show_all.isVisible():
            show_all.click()
        elif show_focus.isVisible():
            show_focus.click()

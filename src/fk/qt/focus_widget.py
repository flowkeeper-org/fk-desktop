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
from PySide6.QtGui import QPainter, QPixmap, Qt, QGradient, QColor, QMouseEvent, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QMenu, QSizePolicy, QToolButton, \
    QSpacerItem

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer_display import AbstractTimerDisplay
from fk.core.event_source_holder import EventSourceHolder
from fk.core.events import AfterSettingsChanged
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_TRACKER
from fk.core.pomodoro_strategies import VoidPomodoroStrategy, StartWorkStrategy, FinishTrackingStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CompleteWorkitemStrategy
from fk.desktop.application import Application, AfterFontsChanged
from fk.qt.actions import Actions
from fk.qt.timer_widget import TimerWidget

logger = logging.getLogger(__name__)
DISPLAY_HEIGHT = 80


def complete_item(item: Workitem, parent: QWidget, source: AbstractEventSource) -> None:
    if item is None:
        raise Exception("Trying to complete a workitem, while there's none selected")
    if not item.has_running_pomodoro() or item.is_tracker() or QMessageBox().warning(
            parent,
            "Confirmation",
            f"Are you sure you want to complete workitem '{item.get_display_name()}'? This will void current pomodoro.",
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Cancel
    ) == QMessageBox.StandardButton.Ok:
        source.execute(CompleteWorkitemStrategy, [item.get_uid(), "finished"])


class FocusWidget(QWidget, AbstractTimerDisplay):
    _settings: AbstractSettings
    _header_text: QLabel
    _header_subtext: QLabel
    _actions: Actions
    _application: Application
    _pixmap: QPixmap | None
    _border_color: QColor
    _continue_workitem: Workitem | None
    _timer_widget: TimerWidget
    _moving_around: QPoint | None
    _hint_label: QLabel | None
    _added: [QWidget]
    _readonly: bool

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings,
                 actions: Actions,
                 flavor: str = 'minimal',
                 readonly: bool = False):
        super().__init__(parent, timer=timer, source_holder=source_holder)

        self._apply_size_policy()

        self._settings = settings
        self._actions = actions
        self._application = application
        self._pixmap = None
        self._continue_workitem = None
        self._moving_around = None
        self._hint_label = None
        self._border_color = QColor('#000000')
        self._timer_widget = None
        self._added = []
        self._readonly = readonly

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
        application.on(AfterFontsChanged, self._on_fonts_changed)
        self._header_text = header_text

        header_subtext = QLabel(self)
        header_subtext.setObjectName('headerSubtext')
        text_layout.addWidget(header_subtext)
        header_subtext.setText("Welcome to Flowkeeper!")
        self._header_subtext = header_subtext

        text_layout.addStretch()

        self.set_flavor(flavor)

        if self._timer is not None:
            if self._timer.is_working():
                self._set_mode('working')
            elif self._timer.is_resting():
                self._set_mode('resting')
            elif self._timer.is_idling():
                self._set_mode('idle')

        self.eye_candy()
        settings.on(AfterSettingsChanged, self._on_setting_changed)

    def set_flavor(self, flavor):
        layout = self.layout()
        last_values = None

        if self._timer_widget is not None:
            # Delete all widgets from the layout
            for w in self._added:
                if isinstance(w, QSpacerItem):
                    layout.removeItem(w)
                else:
                    layout.removeWidget(w)
                    w.deleteLater()
            self._added = []
            last_values = self._timer_widget.get_last_values()

        center_button = None
        if flavor == 'classic':
            # We add both buttons, but one of them will always be hidden
            center_button = QWidget(self)
            center_button.setContentsMargins(0, 0, 0, 0)
            center_button_layout = QHBoxLayout()
            center_button_layout.setContentsMargins(0, 0, 0, 0)
            center_button_layout.setSpacing(0)
            center_button.setLayout(center_button_layout)
            void_pomodoro_button = self._create_button("focus.voidPomodoro")
            center_button_layout.addWidget(void_pomodoro_button)
            self._added.append(void_pomodoro_button)
            finish_tracking_button = self._create_button("focus.finishTracking")
            center_button_layout.addWidget(finish_tracking_button)
            self._added.append(finish_tracking_button)

        self._timer_widget = TimerWidget(self,
                                         'timer',
                                         flavor,
                                         center_button,
                                         63)
        if flavor == 'classic':
            w = self._timer_widget
            self._added.append(w)
            layout.addWidget(w)

            w = self._create_button("focus.nextPomodoro")
            self._added.append(w)
            layout.addWidget(w)

            w = self._create_button("focus.completeItem")
            self._added.append(w)
            layout.addWidget(w)

            if "window.pinWindow" in self._actions:
                w = self._create_button("window.pinWindow")
                self._added.append(w)
                layout.addWidget(w)

        elif flavor == 'minimal':
            w = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding)
            self._added.append(w)
            layout.addSpacerItem(w)

            if self._settings.get('Application.show_click_here_hint') == 'True':
                self._hint_label = self._initialize_hint_label()
                w = self._hint_label
                self._added.append(w)
                layout.addWidget(w)

            self._timer_widget.clicked.connect(self._timer_clicked)

            w = self._timer_widget
            self._added.append(w)
            layout.addWidget(w)

        self._update_colors()
        if last_values is not None:
            self._timer_widget.set_values(**last_values)
        self.mode_changed(self._mode, self._mode)

    def kill(self):
        super().kill()
        self._settings.unsubscribe(self._on_setting_changed)
        self._application.unsubscribe(self._on_fonts_changed)

    def _initialize_hint_label(self) -> QLabel:
        hint_label = QLabel(self)
        hint_label.setObjectName('headerSubSubtext')
        hint_label.setText("Click here →")
        return hint_label

    def update_fonts(self):
        self._header_text.setFont(self._application.get_header_font())

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('focus.voidPomodoro', "Void Pomodoro", 'Ctrl+V', "tool-void", FocusWidget._void_pomodoro)
        actions.add('focus.finishTracking', "Stop Tracking Time", 'Ctrl+S', "tool-finish-tracking", FocusWidget._finish_tracking)
        actions.add('focus.nextPomodoro', "Next Pomodoro", None, "tool-focus-next", FocusWidget._next_pomodoro)
        actions.add('focus.completeItem', "Complete Item", None, "tool-focus-complete", FocusWidget._complete_item)

    def _create_button(self,
                       name: str,
                       parent: QWidget = None):
        action = self._actions[name]
        btn = QToolButton(self if parent is None else parent)
        btn.setObjectName(name)
        btn.setIcon(QIcon(action.icon()))
        btn.setIconSize(QSize(32, 32))
        btn.setDefaultAction(action)
        action.enabledChanged.connect(btn.setVisible)
        btn.setVisible(action.isEnabled())
        return btn

    def reset(self, text: str = 'Idle', subtext: str = "It's time for the next Pomodoro.") -> None:
        self._header_text.setText(text)
        self._header_subtext.setText(subtext)
        if not self._readonly:
            self._actions['focus.completeItem'].setDisabled(True)
            self._actions['focus.voidPomodoro'].setVisible(False)
            self._actions['focus.voidPomodoro'].setDisabled(True)
            self._actions['focus.finishTracking'].setVisible(False)
            self._actions['focus.finishTracking'].setDisabled(True)
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

    def _update_colors(self):
        variables = self._application.get_theme_variables()
        self._border_color = variables['FOCUS_BORDER_COLOR']
        self._timer_widget.fg_color = QColor(variables['FOCUS_TEXT_COLOR'])
        self._timer_widget.bg_color = QColor(variables['FOCUS_BG_COLOR'])

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.theme' in new_values:
            self._update_colors()
        if 'Application.eyecandy_type' in new_values or \
                'Application.eyecandy_gradient' in new_values or \
                'Application.eyecandy_image' in new_values:
            self.eye_candy()
        if self._hint_label is not None and 'Application.show_click_here_hint' in new_values:
            self._hint_label.hide()

    def _on_fonts_changed(self, event, header_font, **kwargs):
        self._header_text.setFont(header_font)

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

    def _finish_tracking(self) -> None:
        for backlog in self._source_holder.get_source().backlogs():
            workitem, _ = backlog.get_running_workitem()
            if workitem is not None:
                self._source_holder.get_source().execute(FinishTrackingStrategy, [workitem.get_uid()])

    def _next_pomodoro(self) -> None:
        settings = self._source_holder.get_settings()
        self._source_holder.get_source().execute(StartWorkStrategy, [
            self._continue_workitem.get_uid(),
            settings.get('Pomodoro.default_work_duration'),
            settings.get('Pomodoro.default_rest_duration'),
        ])

    def _complete_item(self) -> None:
        item = self._timer.get_running_workitem()
        complete_item(item, self, self._source_holder.get_source())

    def tick(self, pomodoro: Pomodoro, state_text: str, my_value: float, my_max: float, mode: str) -> None:
        self._header_text.setText(state_text)
        self._timer_widget.set_values(my_value, my_max, None, None, mode)

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        if new_mode == 'undefined' or new_mode == 'idle':
            self.reset()
            if not self._readonly:
                self._actions['focus.nextPomodoro'].setDisabled(True)
                self._actions['focus.nextPomodoro'].setText('Next Pomodoro')
        elif new_mode == 'working' or new_mode == 'resting':
            running_item = self._timer.get_running_workitem()
            self._header_subtext.setText(running_item.get_display_name())
            if not self._readonly:
                if self._timer.get_running_pomodoro().get_type() == POMODORO_TYPE_TRACKER:
                    self._actions['focus.voidPomodoro'].setVisible(False)
                    self._actions['focus.voidPomodoro'].setDisabled(True)
                    self._actions['focus.finishTracking'].setVisible(True)
                    self._actions['focus.finishTracking'].setDisabled(False)
                else:
                    self._actions['focus.voidPomodoro'].setVisible(True)
                    self._actions['focus.voidPomodoro'].setDisabled(False)
                    self._actions['focus.finishTracking'].setVisible(False)
                    self._actions['focus.finishTracking'].setDisabled(True)
                self._actions['focus.nextPomodoro'].setDisabled(True)
                self._actions['focus.nextPomodoro'].setText(f'Next Pomodoro ({running_item.get_short_display_name()})')
                self._actions['focus.completeItem'].setDisabled(False)
        elif new_mode == 'ready':
            self.reset('Start another Pomodoro?', self._continue_workitem.get_display_name())
            self._timer_widget.set_values(0, 1, None, None, 'ready')
            if not self._readonly:
                self._actions['focus.nextPomodoro'].setDisabled(False)
                self._actions['focus.nextPomodoro'].setText(f'Next Pomodoro ({self._continue_workitem.get_short_display_name()})')

    def _apply_size_policy(self):
        sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp.setVerticalStretch(0)
        self.setSizePolicy(sp)
        self.setMinimumHeight(DISPLAY_HEIGHT)
        self.setMaximumHeight(DISPLAY_HEIGHT)

    def _timer_clicked(self, pos: QPoint) -> None:
        self._settings.set({'Application.show_click_here_hint': 'False'})
        context_menu = QMenu(self)
        context_menu.addAction(self._actions['focus.nextPomodoro'])
        if self._timer.is_working() or self._timer.is_resting():
            if self._timer.get_running_pomodoro().get_type() == POMODORO_TYPE_TRACKER:
                context_menu.addAction(self._actions['focus.finishTracking'])
            else:
                context_menu.addAction(self._actions['focus.voidPomodoro'])
        context_menu.addSeparator()
        context_menu.addAction(self._actions['window.focusMode'])
        context_menu.addAction(self._actions['window.pinWindow'])
        context_menu.addSeparator()
        context_menu.addAction(self._actions['focus.completeItem'])
        context_menu.exec(self._timer_widget.mapToGlobal(pos))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._moving_around = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._moving_around is not None:
            self.window().move(self.window().pos() + event.pos() - self._moving_around)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._moving_around = None

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if not self._readonly:
            self._actions['window.focusMode'].toggle()


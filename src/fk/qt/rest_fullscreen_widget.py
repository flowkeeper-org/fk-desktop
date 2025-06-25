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

from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QMainWindow, QMenu, QHBoxLayout, QToolButton, QSpacerItem, QSizePolicy

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_timer_display import AbstractTimerDisplay
from fk.core.event_source_holder import EventSourceHolder
from fk.core.events import AfterSettingsChanged
from fk.core.pomodoro import Pomodoro
from fk.core.timer import PomodoroTimer
from fk.desktop.application import Application, AfterFontsChanged
from fk.qt.timer_widget import TimerWidget

logger = logging.getLogger(__name__)


class RestFullscreenWidget(QWidget, AbstractTimerDisplay):
    """A fullscreen widget that appears during rest periods."""

    _settings: AbstractSettings
    _application: Application
    _window: QMainWindow
    _message_text: QLabel
    _bg_color: QColor
    _text_color: QColor
    _timer_widget: TimerWidget
    _added: [QWidget]

    def __init__(self,
                 parent: QWidget,
                 application: Application,
                 timer: PomodoroTimer,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings):
        super().__init__(parent, timer=timer, source_holder=source_holder)

        self._added = []

        self._settings = settings
        self._application = application
        self._bg_color = QColor('#2b2b2b')
        self._text_color = QColor('#ffffff')

        self._window = QMainWindow()
        self._window.setWindowTitle("Flowkeeper - Rest Time")
        self._window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self._window.setCentralWidget(self)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Setup timer widget with the appropriate flavor
        flavor = self._settings.get('RestScreen.flavor')
        self.set_flavor(flavor)

        # Message text
        self._message_text = QLabel(self)
        self._message_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_text.setText("")
        application.on(AfterFontsChanged, self._on_fonts_changed)
        layout.addWidget(self._message_text)

        # Subscribe to settings changes
        self._settings.on(AfterSettingsChanged, self._on_setting_changed)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self._bg_color.name()};
                color: {self._text_color.name()};
            }}
            QLabel {{
                color: {self._text_color.name()};
            }}
        """)

    def set_flavor(self, flavor):
        layout = self.layout()
        last_values = None

        if hasattr(self, '_timer_widget') and self._timer_widget is not None:
            # Delete all widgets from the layout except the header and message
            for w in self._added:
                if isinstance(w, QSpacerItem):
                    layout.removeItem(w)
                else:
                    layout.removeWidget(w)
                    w.deleteLater()
            self._added = []
            last_values = self._timer_widget.get_last_values()

        insert_index = 0  # At top

        center_button = None
        if flavor == 'classic':
            # Add timer and action buttons like in FocusWidget
            center_button = QToolButton(self)
            center_button.setContentsMargins(0, 0, 0, 0)
            self._added.append(center_button)


        # Create the timer widget
        self._timer_widget = TimerWidget(self,
                                         'timer',
                                         flavor,
                                         center_button,
                                         256)
        self._added.append(self._timer_widget)
        layout.insertWidget(insert_index, self._timer_widget)


        # Update the timer widget with the previous values if available
        if last_values is not None:
            self._timer_widget.set_values(**last_values)

    def _on_fonts_changed(self, event, header_font, **kwargs):
        self._message_text.setFont(header_font)

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'RestScreen.enabled' in new_values:
            # If disabled while showing, hide the window
            if new_values['RestScreen.enabled'] == 'False' and self._window.isVisible():
                self._window.hide()
        if 'RestScreen.message' in new_values:
            self._message_text.setText(new_values['RestScreen.message'])
        if 'RestScreen.flavor' in new_values:
            self.set_flavor(new_values['RestScreen.flavor'])

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._bg_color)

    def tick(self, pomodoro: Pomodoro, state_text: str, my_value: float, my_max: float, mode: str) -> None:
        if mode in ('resting', 'long-resting'):
            self._timer_widget.set_values(my_value, my_max, None, None, mode)
            self._message_text.setText(state_text)

    def mode_changed(self, old_mode: str, new_mode: str) -> None:
        if self._settings.get('RestScreen.enabled') != 'True':
            return

        if new_mode in ('resting', 'long-resting'):
            # Get the active screen (where the parent window is) or fallback to primary
            active_screen = None
            parent_window = self.parent().window() if self.parent() else None

            if parent_window and parent_window.isVisible():
                # Find the screen containing the parent window
                window_center = parent_window.geometry().center()
                for screen in QApplication.screens():
                    if screen.geometry().contains(window_center):
                        active_screen = screen
                        break

            if not active_screen:
                # Fallback to primary screen if we couldn't determine the active screen
                active_screen = QApplication.primaryScreen()

            # Show full screen on the active screen
            screen_geometry = active_screen.availableGeometry()
            self._window.setGeometry(screen_geometry)
            self._window.showFullScreen()

            # Initial update of the timer
            self._on_tick()
        else:
            # Hide window when not resting
            self._window.hide()

    def kill(self):
        print("RestFullscreenWidget: kill called")
        super().kill()
        self._settings.unsubscribe(self._on_setting_changed)
        self._application.unsubscribe(self._on_fonts_changed)
        self._window.hide()
        self._window.deleteLater()

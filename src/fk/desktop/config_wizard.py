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
import datetime
import os
import sys
from typing import Type

from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QWizard, QWidget, QRadioButton, QMainWindow, QMenu, \
    QHBoxLayout, QSpacerItem, QSizePolicy

from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.focus_widget import FocusWidget
from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer
from fk.qt.qt_settings import QtSettings
from fk.qt.qt_timer import QtTimer
from fk.qt.render.classic_timer_renderer import ClassicTimerRenderer
from fk.qt.timer_widget import TimerWidget
from fk.qt.tray_icon import TrayIcon


def wrap_in_widget(widget: QWidget):
    container = QWidget(widget.parent())
    container.setObjectName('FocusBackground')
    container.setContentsMargins(0, 0, 0, 0)
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    container.setLayout(layout)
    return container


class PageConfigFocus(QWizardPage):
    _tick: int
    _widget1: TimerWidget
    _widget2: TimerWidget

    def __init__(self, application: Application, actions: Actions):
        super().__init__()
        self._tick = 10

        layout_v = QVBoxLayout()

        label = QLabel("This wizard will help you configure Flowkeeper after installation. First choose "
                       "how would you like to see the Focus bar:")
        label.setWordWrap(True)
        layout_v.addWidget(label)

        option_minimal = QRadioButton("Minimalistic", self)
        option_minimal.setChecked(True)
        layout_v.addWidget(option_minimal)

        focus_minimal = FocusWidget(self,
                                    application,
                                    None,
                                    application.get_source_holder(),
                                    application.get_settings(),
                                    actions,
                                    'minimal')
        self._widget1 = focus_minimal._timer_widget
        layout_v.addWidget(wrap_in_widget(focus_minimal))

        option_classic = QRadioButton("Classic", self)
        option_classic.setChecked(False)
        layout_v.addWidget(option_classic)

        focus_classic = FocusWidget(self,
                                    application,
                                    None,
                                    application.get_source_holder(),
                                    application.get_settings(),
                                    actions,
                                    'classic')
        self._widget2 = focus_classic._timer_widget
        layout_v.addWidget(wrap_in_widget(focus_classic))

        label = QLabel("You can change this in Settings > Appearance")
        label.setWordWrap(True)
        layout_v.addWidget(label)

        self.setLayout(layout_v)

        self._timer = QtTimer('Configuration wizard step 1')
        self._timer.schedule(1000, self._handle_tick, None)
        self._handle_tick()

    def _handle_tick(self, params: dict | None = None, when: datetime.datetime | None = None) -> None:
        self._widget1.set_values(self._tick, 10, None, None, 'working')
        self._widget2.set_values(self._tick, 10, None, None, 'working')
        self._tick -= 1
        if self._tick < 0:
            self._tick = 10


class FakeTrayIcon(TrayIcon):
    _tray: QLabel
    _kind: str
    _state: str

    def __init__(self, tray: QLabel, actions: Actions, kind: str, state: str, cls: Type[AbstractTimerRenderer]):
        self._tray = tray
        self._kind = kind
        self._state = state
        super(FakeTrayIcon, self).__init__(tray, None, None, actions, 22, cls, kind == 'Dark')
        self.mode_changed(None, state)

    def setIcon(self, icon: QIcon | QPixmap) -> None:
        if type(icon) is QIcon:
            icon = icon.pixmap(22, 22)
        self._tray.setPixmap(icon)

    def showMessage(self, title: str, msg: str, icon: QIcon = None, **_) -> None:
        pass

    def setToolTip(self, tip: str) -> None:
        self._tray.setToolTip(tip)

    def setContextMenu(self, menu: QMenu) -> None:
        pass


class PageConfigIcons(QWizardPage):
    _actions: Actions

    def __init__(self, actions: Actions):
        super().__init__()
        self._actions = actions

        layout_v = QVBoxLayout()
        label = QLabel("Now choose how you prefer your icons:")
        label.setWordWrap(True)
        layout_v.addWidget(label)

        option_monochrome_light = QRadioButton("Monochrome light", self)
        option_monochrome_light.setChecked(True)
        layout_v.addWidget(option_monochrome_light)
        widget_tray_light = QWidget(self)
        widget_tray_light.setObjectName('trayLight')
        self._create_icons(widget_tray_light, 'Light', MinimalTimerRenderer)
        layout_v.addWidget(widget_tray_light)

        option_monochrome_dark = QRadioButton("Monochrome dark", self)
        option_monochrome_dark.setChecked(False)
        layout_v.addWidget(option_monochrome_dark)
        widget_tray_dark = QWidget(self)
        widget_tray_dark.setObjectName('trayDark')
        self._create_icons(widget_tray_dark, 'Dark', MinimalTimerRenderer)
        layout_v.addWidget(widget_tray_dark)

        option_classic_light = QRadioButton("Classic light", self)
        option_classic_light.setChecked(False)
        layout_v.addWidget(option_classic_light)
        widget_tray_classic_light = QWidget(self)
        widget_tray_classic_light.setObjectName('trayLight')
        self._create_icons(widget_tray_classic_light, 'Light', ClassicTimerRenderer)
        layout_v.addWidget(widget_tray_classic_light)

        option_classic_dark = QRadioButton("Classic dark", self)
        option_classic_dark.setChecked(False)
        layout_v.addWidget(option_classic_dark)
        widget_tray_classic_dark = QWidget(self)
        widget_tray_classic_dark.setObjectName('trayDark')
        self._create_icons(widget_tray_classic_dark, 'Dark', ClassicTimerRenderer)
        layout_v.addWidget(widget_tray_classic_dark)

        self.setLayout(layout_v)

    def _create_icons(self, container: QWidget, kind: str, cls: Type[AbstractTimerRenderer]):
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        icon_size = 22
        container.setLayout(layout)

        workitem = Workitem('N/A',
                            '1',
                            None,
                            datetime.datetime.now())
        pomodoro = Pomodoro(True,
                            'new',
                            25 * 60 * 1000,
                            5 * 60 * 1000,
                            '1',
                            workitem,
                            datetime.datetime.now())

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding))

        icon1 = QLabel('', container)
        icon1.setFixedHeight(icon_size)
        FakeTrayIcon(icon1, self._actions, kind, 'idle', cls).reset()
        layout.addWidget(icon1)

        icon2 = QLabel('', container)
        icon2.setFixedHeight(icon_size)
        f2 = FakeTrayIcon(icon2, self._actions, kind, 'working', cls)
        f2.tick(pomodoro, 'Working', 0.33, 1, 'working')
        layout.addWidget(icon2)

        icon3 = QLabel('', container)
        icon3.setFixedHeight(icon_size)
        f3 = FakeTrayIcon(icon3, self._actions, kind, 'resting', cls)
        f3.tick(pomodoro, 'Resting', 0.66, 1, 'resting')
        layout.addWidget(icon3)

        icon4 = QLabel('', container)
        icon4.setFixedHeight(icon_size)
        FakeTrayIcon(icon4, self._actions, kind, 'ready', cls)
        layout.addWidget(icon4)

        clock = QLabel(datetime.datetime.now().time().strftime('%H:%M'), container)
        clock.setObjectName(f'fakeClock{kind}')
        layout.addWidget(clock)


class ConfigWizard(QWizard):
    page_focus: PageConfigFocus
    page_icons: PageConfigIcons

    def __init__(self, application: Application, actions: Actions, parent: QWidget | None):
        super().__init__(parent)
        self._settings = application.get_settings()
        self.setWindowTitle("First-time configuration")
        self.page_focus = PageConfigFocus(application, actions)
        self.page_icons = PageConfigIcons(actions)
        self.addPage(self.page_focus)
        self.addPage(self.page_icons)

        # Account for a Qt bug which shrinks dialogs opened on non-primary displays
        self.setMinimumSize(600, 500)
        if os.name == 'nt':
            # AeroStyle is default on Windows 11, but it looks all white (another Qt bug?) The Classic style looks fine.
            self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)


if __name__ == '__main__':
    app = Application([])
    window = QMainWindow()
    actions = Actions(window, app.get_settings())
    FocusWidget.define_actions(actions)
    from fk.desktop.desktop import MainWindow
    MainWindow.define_actions(actions)
    settings = QtSettings()
    wizard = ConfigWizard(app, actions, None)
    wizard.show()
    sys.exit(app.exec())

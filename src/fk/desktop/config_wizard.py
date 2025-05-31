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
from typing import Type

from PySide6.QtCore import Signal
from PySide6.QtGui import QPixmap, QIcon, QHideEvent, Qt
from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QWizard, QWidget, QRadioButton, QMenu, \
    QHBoxLayout, QSpacerItem, QSizePolicy

from fk.core.abstract_settings import AbstractSettings
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL
from fk.core.workitem import Workitem
from fk.desktop.application import Application
from fk.qt.actions import Actions
from fk.qt.focus_widget import FocusWidget
from fk.qt.qt_timer import QtTimer
from fk.qt.render.abstract_timer_renderer import AbstractTimerRenderer
from fk.qt.render.classic_timer_renderer import ClassicTimerRenderer
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer
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
    _focus1: FocusWidget
    _widget1: TimerWidget
    _option_minimal: QRadioButton
    _focus2: FocusWidget
    _widget2: TimerWidget
    _option_classic: QRadioButton

    def __init__(self, application: Application, actions: Actions):
        super().__init__()
        self._tick = 10
        flavor = application.get_settings().get('Application.focus_flavor')

        layout_v = QVBoxLayout()

        label = QLabel("This wizard will help you configure Flowkeeper after installation. First choose "
                       "how would you like to see the Focus bar:")
        label.setWordWrap(True)
        layout_v.addWidget(label)

        self._option_minimal = QRadioButton("Minimalistic", self)
        self._option_minimal.setChecked(flavor == 'minimal')
        layout_v.addWidget(self._option_minimal)

        focus_minimal = FocusWidget(self,
                                    application,
                                    None,
                                    application.get_source_holder(),
                                    application.get_settings(),
                                    actions,
                                    'minimal',
                                    True)
        self._widget1 = focus_minimal._timer_widget
        layout_v.addWidget(wrap_in_widget(focus_minimal))
        self._focus1 = focus_minimal

        self._option_classic = QRadioButton("Classic", self)
        self._option_classic.setChecked(flavor == 'classic')
        layout_v.addWidget(self._option_classic)

        focus_classic = FocusWidget(self,
                                    application,
                                    None,
                                    application.get_source_holder(),
                                    application.get_settings(),
                                    actions,
                                    'classic',
                                    True)
        self._widget2 = focus_classic._timer_widget
        layout_v.addWidget(wrap_in_widget(focus_classic))
        self._focus2 = focus_classic

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

    def get_setting(self) -> str:
        return 'classic' if self._option_classic.isChecked() else 'minimal'

    def unsubscribe(self) -> None:
        self._timer.cancel()
        self._focus1.kill()
        self._focus2.kill()


class FakeTrayIcon(TrayIcon):
    _tray: QLabel
    _kind: str
    _state: str

    def __init__(self,
                 tray: QLabel,
                 actions: Actions,
                 kind: str,
                 state: str,
                 cls: Type[AbstractTimerRenderer]):
        self._tray = tray
        self._kind = kind
        self._state = state
        super(FakeTrayIcon, self).__init__(tray,
                                           None,
                                           None,
                                           actions,
                                           48,
                                           cls,
                                           kind == 'Dark')
        self.mode_changed(None, state)

    def setIcon(self, icon: QIcon | QPixmap) -> None:
        if type(icon) is QIcon:
            icon = icon.pixmap(22, 22)
        else:
            pixmap: QPixmap = icon
            icon = pixmap.scaled(22, 22, mode=Qt.TransformationMode.SmoothTransformation)
        self._tray.setPixmap(icon)

    def showMessage(self, title: str, msg: str, icon: QIcon = None, **_) -> None:
        pass

    def setToolTip(self, tip: str) -> None:
        self._tray.setToolTip(tip)

    def setContextMenu(self, menu: QMenu) -> None:
        pass


class PageConfigIcons(QWizardPage):
    _actions: Actions
    _option_classic_light: QRadioButton
    _option_thin_light: QRadioButton
    _option_classic_dark: QRadioButton
    _option_thin_dark: QRadioButton

    def __init__(self, application: Application, actions: Actions):
        super().__init__()
        self._actions = actions
        flavor = application.get_settings().get('Application.tray_icon_flavor')

        layout_v = QVBoxLayout()
        label = QLabel("Now choose how you prefer your icons:")
        label.setWordWrap(True)
        layout_v.addWidget(label)

        self._option_thin_light = QRadioButton("Thin, light background", self)
        self._option_thin_light.setChecked(flavor == 'thin-light')
        layout_v.addWidget(self._option_thin_light)
        widget_tray_light = QWidget(self)
        widget_tray_light.setObjectName('trayLight')
        self._create_icons(widget_tray_light, 'Light', MinimalTimerRenderer)
        layout_v.addWidget(widget_tray_light)

        self._option_thin_dark = QRadioButton("Thin, dark background", self)
        self._option_thin_dark.setChecked(flavor == 'thin-dark')
        layout_v.addWidget(self._option_thin_dark)
        widget_tray_dark = QWidget(self)
        widget_tray_dark.setObjectName('trayDark')
        self._create_icons(widget_tray_dark, 'Dark', MinimalTimerRenderer)
        layout_v.addWidget(widget_tray_dark)

        self._option_classic_light = QRadioButton("Classic, light background", self)
        self._option_classic_light.setChecked(flavor == 'classic-light')
        layout_v.addWidget(self._option_classic_light)
        widget_tray_classic_light = QWidget(self)
        widget_tray_classic_light.setObjectName('trayLight')
        self._create_icons(widget_tray_classic_light, 'Light', ClassicTimerRenderer)
        layout_v.addWidget(widget_tray_classic_light)

        self._option_classic_dark = QRadioButton("Classic, dark background", self)
        self._option_classic_dark.setChecked(flavor == 'classic-dark')
        layout_v.addWidget(self._option_classic_dark)
        widget_tray_classic_dark = QWidget(self)
        widget_tray_classic_dark.setObjectName('trayDark')
        self._create_icons(widget_tray_classic_dark, 'Dark', ClassicTimerRenderer)
        layout_v.addWidget(widget_tray_classic_dark)

        self.setLayout(layout_v)
        self.setFinalPage(True)

    def _create_icons(self, container: QWidget, kind: str, cls: Type[AbstractTimerRenderer]):
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        icon_size = 22
        container.setLayout(layout)

        workitem = Workitem('N/A',
                            '1',
                            None,
                            datetime.datetime.now())
        pomodoro = Pomodoro(1,
                            True,
                            'new',
                            25 * 60 * 1000,
                            5 * 60 * 1000,
                            POMODORO_TYPE_NORMAL,
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

    def get_setting(self) -> str:
        if self._option_classic_light.isChecked():
            return 'classic-light'
        elif self._option_thin_light.isChecked():
            return 'thin-light'
        elif self._option_classic_dark.isChecked():
            return 'classic-dark'
        elif self._option_thin_dark.isChecked():
            return 'thin-dark'


class ConfigWizard(QWizard):
    _page_focus: PageConfigFocus
    _page_icons: PageConfigIcons
    _settings: AbstractSettings

    closed = Signal(None)

    def __init__(self, application: Application, actions: Actions, parent: QWidget | None):
        super().__init__(parent)
        self._settings = application.get_settings()
        self._page_focus = PageConfigFocus(application, actions)
        self._page_icons = PageConfigIcons(application, actions)
        self.addPage(self._page_focus)
        self.addPage(self._page_icons)
        self.setWindowTitle("First-time configuration")

        # Account for a Qt bug which shrinks dialogs opened on non-primary displays
        self.setMinimumSize(600, 500)
        if os.name == 'nt':
            # AeroStyle is default on Windows 11, but it looks all white (another Qt bug?) The Classic style looks fine.
            self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(self._on_finish)
        self.closed.connect(self.unsubscribe)

    def _on_finish(self):
        self._settings.set({
            'Application.focus_flavor': self._page_focus.get_setting(),
            'Application.tray_icon_flavor': self._page_icons.get_setting(),
        })

    def unsubscribe(self):
        self._page_focus.unsubscribe()

    def hideEvent(self, event: QHideEvent) -> None:
        super(ConfigWizard, self).hideEvent(event)
        self.closed.emit()

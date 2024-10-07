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
import sys
import threading

from PySide6 import QtCore, QtWidgets, QtUiTools, QtAsyncio
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import AfterWorkitemComplete, SourceMessagesProcessed
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.desktop.application import Application, AfterSourceChanged
from fk.desktop.tutorial import Tutorial
from fk.qt.abstract_tableview import AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.audio_player import AudioPlayer
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.backlog_widget import BacklogWidget
from fk.qt.connection_widget import ConnectionWidget
from fk.qt.focus_widget import FocusWidget
from fk.qt.progress_widget import ProgressWidget
from fk.qt.qt_settings import QtSettings
from fk.qt.qt_timer import QtTimer
from fk.qt.resize_event_filter import ResizeEventFilter
from fk.qt.search_completer import SearchBar
from fk.qt.theme_change_event_filter import ThemeChangeEventFilter
from fk.qt.tray_icon import TrayIcon
from fk.qt.user_tableview import UserTableView
from fk.qt.workitem_tableview import WorkitemTableView
from fk.qt.workitem_widget import WorkitemWidget

logger = logging.getLogger(__name__)


def get_timer_ui_mode() -> str:
    # Options: keep (don't do anything), focus (collapse main layout), minimize (window to tray)
    return settings.get('Application.timer_ui_mode')


def set_window_flags(is_focused: bool):
    flags = default_flags

    hide_frame = settings.get('Application.show_window_title') != 'True'
    mode = get_timer_ui_mode()
    if mode == 'focus' and is_focused and hide_frame:
        flags = flags | Qt.WindowType.FramelessWindowHint

    is_pinned = settings.get('Application.always_on_top') == 'True'
    if is_pinned:
        flags = flags | Qt.WindowType.WindowStaysOnTopHint

    window.setWindowFlags(flags)


def show_timer_automatically() -> None:
    global continue_workitem
    actions['focus.voidPomodoro'].setEnabled(True)
    mode = get_timer_ui_mode()
    if mode == 'focus':
        set_window_flags(True)
        height = focus.size().height()
        focus.show()
        main_layout.hide()
        left_toolbar.hide()
        window.setFixedWidth(window.width())    # TODO: Make it flexible
        window.setFixedHeight(height)
        window.adjustSize()
        focus._buttons['window.showFocus'].hide()
        focus._buttons['window.showAll'].show()
        window.show()
    elif mode == 'minimize':
        window.hide()


def hide_timer(event: str|None = None, **kwargs) -> None:
    set_window_flags(False)
    main_layout.show()
    focus.show()
    left_toolbar.show()
    window.setMaximumHeight(16777215)
    window.setMinimumHeight(0)
    window.setMaximumWidth(16777215)
    window.setMinimumWidth(0)
    resize_event_filter.restore_size()
    focus._buttons['window.showFocus'].show()
    focus._buttons['window.showAll'].hide()
    window.show()

    # Without this junk with Qt 6.7.0, KDE 5.18.8 on XOrg the window moves down every time its size is restored
    pos = window.pos()
    pos.setY(pos.y() - 1)
    window.move(pos)
    pos.setY(pos.y() + 1)
    window.move(pos)


def hide_timer_automatically() -> None:
    actions['focus.voidPomodoro'].setDisabled(True)
    mode = get_timer_ui_mode()
    if mode == 'focus':
        focus._buttons['window.showFocus'].show()
        focus._buttons['window.showAll'].hide()
        hide_timer()
    elif mode == 'minimize':
        window.show()


def update_tables_visibility() -> None:
    users_visible = (settings.get('Application.users_visible') == 'True')
    users_table.setVisible(users_visible)
    backlogs_visible = (settings.get('Application.backlogs_visible') == 'True')
    backlogs_widget.setVisible(backlogs_visible)
    left_table_layout.setVisible(users_visible or backlogs_visible)


def on_messages(event: str, source: AbstractEventSource, carry: any = None) -> None:
    if pomodoro_timer.is_working() or pomodoro_timer.is_resting():
        show_timer_automatically()


def on_setting_changed(event: str, old_values: dict[str, str], new_values: dict[str, str]):
    logger.debug(f'Settings changed from {old_values} to {new_values}')

    status.showMessage('Settings changed')
    for name in new_values.keys():
        new_value = new_values[name]
        if name == 'Application.timer_ui_mode' and (pomodoro_timer.is_working() or pomodoro_timer.is_resting()):
            # TODO: This really doesn't work well
            hide_timer_automatically()
            show_timer_automatically()
        elif name == 'Application.show_main_menu':
            main_menu.setVisible(new_value == 'True')
        elif name == 'Application.show_status_bar':
            status.setVisible(new_value == 'True')
        elif name == 'Application.show_left_toolbar':
            left_toolbar.setVisible(new_value == 'True')
        elif name == 'Application.show_tray_icon':
            tray.setVisible(new_value == 'True')
        elif name == 'Application.shortcuts':
            actions.update_from_settings()
        elif name == 'Application.always_on_top':
            set_window_flags(main_layout.isHidden())
            window.show()


class MainWindow:
    def __init__(self):
        super().__init__()

    def show_all(self):
        hide_timer()

    def show_focus(self):
        show_timer_automatically()

    def pin_window(self):
        settings.set({'Application.always_on_top': 'True'})

    def unpin_window(self):
        settings.set({'Application.always_on_top': 'False'})

    def show_window(self):
        window.show()

    def show_search(self):
        search.show()

    def toggle_backlogs(self, enabled):
        settings.set({'Application.backlogs_visible': str(enabled)})
        update_tables_visibility()

    def toggle_users(self, enabled):
        settings.set({'Application.users_visible': str(enabled)})
        update_tables_visibility()

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('window.showAll', "Show All", None, "tool-show-all", MainWindow.show_all)
        actions.add('window.showFocus', "Show Focus", None, "tool-show-timer-only", MainWindow.show_focus)
        actions.add('window.pinWindow', "Pin Flowkeeper", None, "tool-pin", MainWindow.pin_window)
        actions.add('window.unpinWindow', "Unpin Flowkeeper", None, "tool-unpin", MainWindow.unpin_window)
        actions.add('window.showMainWindow', "Show Main Window", None, "tool-show-timer-only", MainWindow.show_window)
        actions.add('window.showSearch', "Search...", 'Ctrl+F', '', MainWindow.show_search)

        backlogs_were_visible = (settings.get('Application.backlogs_visible') == 'True')
        actions.add('window.showBacklogs',
                    "Backlogs",
                    'Ctrl+B',
                    'tool-backlogs',
                    MainWindow.toggle_backlogs,
                    True,
                    backlogs_were_visible)

        users_were_visible = (settings.get('Application.users_visible') == 'True')
        actions.add('window.showUsers',
                    "Team",
                    'Ctrl+T',
                    'tool-teams',
                    MainWindow.toggle_users,
                    True,
                    settings.is_team_supported() and users_were_visible)


if __name__ == "__main__":
    # The order is important here. Some Sources use Qt APIs, so we need an Application instance created first.
    # Then we initialize a Source. This needs to happen before we configure UI, because the Source will replay
    # Strategies in __init__, and we don't want anyone to be subscribed to their events yet. It will build the
    # data model. Once the Source is constructed, we can initialize the rest of the UI, including Qt data models.
    # From that moment we can respond to user actions and events from the backend, which the Source + Strategies
    # will pass through to Qt data models via Qt-like connect / emit mechanism.
    try:
        settings = None
        app = Application(sys.argv)
        settings = app.get_settings()

        logger.debug(f'UI thread: {threading.get_ident()}')
        settings.on(events.AfterSettingsChanged, on_setting_changed)

        def _on_source_changed(event: str, source: AbstractEventSource):
            main_window.show_all()
            source.on(SourceMessagesProcessed, on_messages)
            source.on(AfterWorkitemComplete, hide_timer)

        app.get_source_holder().on(AfterSourceChanged, _on_source_changed)

        pomodoro_timer = PomodoroTimer(QtTimer("Pomodoro Tick"), QtTimer("Pomodoro Transition"), app.get_settings(), app.get_source_holder())
        pomodoro_timer.on(PomodoroTimer.TimerRestComplete, lambda timer, workitem, pomodoro, event: hide_timer_automatically())
        pomodoro_timer.on(PomodoroTimer.TimerWorkStart, lambda timer, event: show_timer_automatically())

        loader = QtUiTools.QUiLoader()

        # Load main window
        file = QtCore.QFile(":/core.ui")
        file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        window: QtWidgets.QMainWindow = loader.load(file, None)
        file.close()

        default_flags = window.windowFlags()

        # Collect actions from all widget types
        actions = Actions(window, settings)
        Application.define_actions(actions)
        BacklogTableView.define_actions(actions)
        UserTableView.define_actions(actions)
        WorkitemTableView.define_actions(actions)
        FocusWidget.define_actions(actions)
        MainWindow.define_actions(actions)
        actions.all_actions_defined()

        audio = AudioPlayer(window, app.get_source_holder(), settings, pomodoro_timer)

        # File menu
        menu_file = QtWidgets.QMenu("File", window)
        menu_file.addAction(actions['application.settings'])
        menu_file.addAction(actions['application.import'])
        menu_file.addAction(actions['application.export'])
        menu_file.addAction(actions['application.stats'])
        menu_file.addAction(actions['application.workSummary'])
        menu_file.addSeparator()
        menu_file.addAction(actions['application.about'])
        menu_file.addSeparator()
        menu_file.addAction(actions['application.quit'])

        # noinspection PyTypeChecker
        left_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "leftTableLayoutInternal")

        # noinspection PyTypeChecker
        left_toolbar_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "left_toolbar_layout")
        left_toolbar_layout.addWidget(ConnectionWidget(window, app))

        # Backlogs table
        backlogs_widget: BacklogWidget = BacklogWidget(window, app, app.get_source_holder(), actions)
        backlogs_widget.get_table().on(AfterSelectionChanged, lambda event, before, after: workitems_widget.upstream_selected(after))
        backlogs_widget.get_table().on(AfterSelectionChanged, lambda event, before, after: progress_widget.update_progress(after) if after is not None else None)
        left_layout.addWidget(backlogs_widget)

        # Users table
        users_table: UserTableView = UserTableView(window, app, app.get_source_holder(), actions)
        left_layout.addWidget(users_table)

        # noinspection PyTypeChecker
        right_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rightTableLayoutInternal")

        # Workitems table
        workitems_widget: WorkitemWidget = WorkitemWidget(window, app, app.get_source_holder(), actions)
        right_layout.addWidget(workitems_widget)

        progress_widget = ProgressWidget(window, app.get_source_holder())
        right_layout.addWidget(progress_widget)

        # noinspection PyTypeChecker
        search_bar: QtWidgets.QHBoxLayout = window.findChild(QtWidgets.QHBoxLayout, "searchBar")
        search = SearchBar(window,
                           app.get_source_holder(),
                           actions,
                           backlogs_widget.get_table(),
                           workitems_widget.get_table())
        search_bar.addWidget(search)

        # noinspection PyTypeChecker
        root_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rootLayoutInternal")
        focus = FocusWidget(window, app, pomodoro_timer, app.get_source_holder(), settings, actions)
        root_layout.insertWidget(0, focus)

        # Layouts
        # noinspection PyTypeChecker
        main_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "mainLayout")
        # noinspection PyTypeChecker
        left_table_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "leftTableLayout")

        # Connect menu actions to the toolbar
        # TODO -- migrate all those to Actions and remove all actions from .ui file

        # noinspection PyTypeChecker
        action_backlogs = actions['window.showBacklogs']
        action_teams = actions['window.showUsers']

        # Main menu
        # noinspection PyTypeChecker
        main_menu: QtWidgets.QMenuBar = window.findChild(QtWidgets.QMenuBar, "menuBar")
        if main_menu is not None:
            show_main_menu = (settings.get('Application.show_main_menu') == 'True')
            main_menu.setVisible(show_main_menu)

        # Status bar
        # noinspection PyTypeChecker
        status: QtWidgets.QStatusBar = window.findChild(QtWidgets.QStatusBar, "statusBar")
        if status is not None:
            show_status_bar = (settings.get('Application.show_status_bar') == 'True')
            status.showMessage('Ready')
            status.setVisible(show_status_bar)

        # Tray icon
        show_tray_icon = (settings.get('Application.show_tray_icon') == 'True')
        tray = TrayIcon(window, pomodoro_timer, app.get_source_holder(), actions)
        tray.setVisible(show_tray_icon)

        # Some global variables to support "Next pomodoro" mode
        # TODO Empty it if it gets deleted or completed
        continue_workitem: Workitem | None = None

        # Left toolbar
        # noinspection PyTypeChecker
        left_toolbar: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "left_toolbar")
        show_left_toolbar = (settings.get('Application.show_left_toolbar') == 'True')
        left_toolbar.setVisible(show_left_toolbar)

        # noinspection PyTypeChecker
        tool_backlogs: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolBacklogs")
        tool_backlogs.setIcon(QIcon.fromTheme('tool-backlogs'))
        tool_backlogs.setDefaultAction(action_backlogs)

        # noinspection PyTypeChecker
        tool_teams: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolTeams")
        tool_teams.setIcon(QIcon.fromTheme('tool-teams'))
        tool_teams.setDefaultAction(action_teams)
        action_teams.setEnabled(settings.is_team_supported())
        tool_teams.setVisible(settings.is_team_supported())

        # noinspection PyTypeChecker
        tool_settings: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolSettings")
        tool_settings.setIcon(QIcon.fromTheme('tool-menu'))
        tool_settings.clicked.connect(lambda: menu_file.exec(
            tool_settings.parentWidget().mapToGlobal(tool_settings.geometry().center())
        ))

        # Restore window config from settings
        update_tables_visibility()

        resize_event_filter = ResizeEventFilter(window, main_layout, settings)
        window.installEventFilter(resize_event_filter)
        window.move(app.primaryScreen().geometry().center() - window.frameGeometry().center())

        theme_change_event_filter = ThemeChangeEventFilter(window, settings)
        window.installEventFilter(theme_change_event_filter)

        main_window = MainWindow()

        # Bind action domains to widget instances
        actions.bind('application', app)
        actions.bind('backlogs_table', backlogs_widget.get_table())
        actions.bind('users_table', users_table)
        actions.bind('workitems_table', workitems_widget.get_table())
        actions.bind('focus', focus)
        actions.bind('window', main_window)

        set_window_flags(False)

        tutorial = Tutorial(app.get_source_holder(), settings, window)

        window.show()

        # With Qt 6.7.1 on Windows this needs to happen AFTER the Window is shown.
        # Otherwise, the font size for the focus' header is picked correctly, but
        # default font family is used.
        focus.update_fonts()

        try:
            app.initialize_source()
        except Exception as ex:
            app.on_exception(type(ex), ex, ex.__traceback__)

        if app.is_e2e_mode():
            # Our end-to-end tests use asyncio.sleep() extensively, so we need Qt event loop to support coroutines.
            # This is an experimental feature in Qt 6.6.2+.
            QtAsyncio.run()
        else:
            if '--reset' in app.arguments():
                settings.reset_to_defaults()
            # This would work on any Qt 6.6.x
            sys.exit(app.exec())

    except Exception as exc:
        logger.error("FATAL: Exception on startup", exc_info=exc)
        if '--version' in sys.argv:
            # We don't want to display anything blocking here
            exit(2)
        res = QMessageBox().critical(None,
                                     "Startup error",
                                     f"Something unexpected has happened during Flowkeeper startup. It is most likely "
                                     f"due to some wrong setting, which crashes Flowkeeper. \n\nYou can try fixing it "
                                     f"yourself by checking "
                                     f"{settings.location() if settings is not None else 'settings file'}.\n\n"
                                     f"Alternatively, if you click 'Restore Defaults' to restore Flowkeeper settings to their "
                                     f"default values. This includes data source and connection settings like your "
                                     f"saved authentication credentials. You will NOT lose your data if you click Reset.",
                                     QMessageBox.StandardButton.RestoreDefaults,
                                     QMessageBox.StandardButton.Close)
        if res == QMessageBox.StandardButton.RestoreDefaults:
            QtSettings().reset_to_defaults()
            QMessageBox().information(None,
                                      "Startup error",
                                      f"To finish resetting its configuration, Flowkeeper will now close.",
                                      QMessageBox.StandardButton.Ok)

        logger.debug('Exiting')
        sys.exit(2)

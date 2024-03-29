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
import sys
import threading

from PySide6 import QtCore, QtWidgets, QtUiTools

from fk.core import events
from fk.core.events import AfterWorkitemComplete, SourceMessagesProcessed
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.desktop.application import Application
from fk.qt.abstract_tableview import AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.audio_player import AudioPlayer
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.connection_widget import ConnectionWidget
from fk.qt.focus_widget import FocusWidget
from fk.qt.progress_widget import ProgressWidget
from fk.qt.qt_timer import QtTimer
from fk.qt.resize_event_filter import ResizeEventFilter
from fk.qt.search_completer import SearchBar
from fk.qt.tray_icon import TrayIcon
from fk.qt.user_tableview import UserTableView
from fk.qt.workitem_tableview import WorkitemTableView


def get_timer_ui_mode() -> str:
    # Options: keep (don't do anything), focus (collapse main layout), minimize (window to tray)
    return settings.get('Application.timer_ui_mode')


def show_timer_automatically() -> None:
    global continue_workitem
    actions['focus.voidPomodoro'].setEnabled(True)
    mode = get_timer_ui_mode()
    if mode == 'focus':
        focus.show()
        main_layout.hide()
        left_toolbar.hide()
        window.setMaximumHeight(focus.size().height())
        window.setMinimumHeight(focus.size().height())
        focus._buttons['window.showFocus'].hide()
        focus._buttons['window.showAll'].show()
    elif mode == 'minimize':
        window.hide()


def hide_timer(event: str|None = None, **kwargs) -> None:
    main_layout.show()
    focus.show()
    left_toolbar.show()
    window.setMaximumHeight(16777215)
    window.setMinimumHeight(0)
    event_filter.restore_size()
    focus._buttons['window.showFocus'].show()
    focus._buttons['window.showAll'].hide()


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
    backlogs_table.setVisible(backlogs_visible)
    left_table_layout.setVisible(users_visible or backlogs_visible)


def on_messages(event) -> None:
    if pomodoro_timer.is_working() or pomodoro_timer.is_resting():
        show_timer_automatically()


def on_setting_changed(event: str, name: str, old_value: str, new_value: str):
    # print(f'Setting {name} changed from {old_value} to {new_value}')
    status.showMessage('Settings changed')
    if name == 'Application.timer_ui_mode' and (pomodoro_timer.is_working() or pomodoro_timer.is_resting()):
        # TODO: This really doesn't work well
        hide_timer_automatically()
        show_timer_automatically()
    elif name == 'Application.show_main_menu':
        main_menu.setVisible(new_value == 'True')
    elif name == 'Application.show_status_bar':
        status.setVisible(new_value == 'True')
    elif name == 'Application.show_toolbar':
        toolbar.setVisible(new_value == 'True')
    elif name == 'Application.show_left_toolbar':
        left_toolbar.setVisible(new_value == 'True')
    elif name == 'Application.show_tray_icon':
        tray.setVisible(new_value == 'True')
    elif name == 'Application.shortcuts':
        actions.update_from_settings()
    # TODO: Reload the app when the source changes


class MainWindow:
    def show_all(self):
        hide_timer()

    def show_focus(self):
        show_timer_automatically()

    def show_window(self):
        window.show()

    def show_search(self):
        search.show()

    def toggle_backlogs(self, enabled):
        settings.set('Application.backlogs_visible', str(enabled))
        update_tables_visibility()

    def toggle_users(self, enabled):
        settings.set('Application.users_visible', str(enabled))
        update_tables_visibility()

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('window.showAll', "Show All", None, ":/icons/tool-show-all.svg", MainWindow.show_all)
        actions.add('window.showFocus', "Show Focus", None, ":/icons/tool-show-timer-only.svg", MainWindow.show_focus)
        actions.add('window.showMainWindow', "Show Main Window", None, ":/icons/tool-show-timer-only.svg", MainWindow.show_window)
        actions.add('window.showSearch', "Search...", 'Ctrl+F', '', MainWindow.show_search)

        backlogs_were_visible = (settings.get('Application.backlogs_visible') == 'True')
        actions.add('window.showBacklogs',
                    "Backlogs",
                    'Ctrl+B',
                    ':/icons/tool-backlogs.svg',
                    MainWindow.toggle_backlogs,
                    True,
                    backlogs_were_visible)

        users_were_visible = (settings.get('Application.users_visible') == 'True')
        actions.add('window.showUsers',
                    "Team",
                    'Ctrl+T',
                    ':/icons/tool-teams.svg',
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
    app = Application(sys.argv)

    print('UI thread:', threading.get_ident())

    settings = app.get_settings()
    settings.on(events.AfterSettingChanged, on_setting_changed)

    source = app.get_source()
    source.on(SourceMessagesProcessed, on_messages)

    pomodoro_timer = PomodoroTimer(source, QtTimer("Pomodoro Tick"), QtTimer("Pomodoro Transition"))
    pomodoro_timer.on("TimerRestComplete", lambda timer, workitem, pomodoro, event: hide_timer_automatically())
    pomodoro_timer.on("TimerWorkStart", lambda timer, event: show_timer_automatically())

    loader = QtUiTools.QUiLoader()

    # Load main window
    file = QtCore.QFile(":/core.ui")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    # noinspection PyTypeChecker
    window: QtWidgets.QMainWindow = loader.load(file, None)
    file.close()

    # Collect actions from all widget types
    actions = Actions(window, settings)
    Application.define_actions(actions)
    BacklogTableView.define_actions(actions)
    UserTableView.define_actions(actions)
    WorkitemTableView.define_actions(actions)
    FocusWidget.define_actions(actions)
    MainWindow.define_actions(actions)

    audio = AudioPlayer(window, source, settings, pomodoro_timer)

    # File menu
    menu_file = QtWidgets.QMenu("File", window)
    menu_file.addAction(actions['application.settings'])
    menu_file.addAction(actions['application.import'])
    menu_file.addAction(actions['application.export'])
    menu_file.addSeparator()
    menu_file.addAction(actions['application.about'])
    menu_file.addSeparator()
    menu_file.addAction(actions['application.quit'])

    # noinspection PyTypeChecker
    left_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "leftTableLayoutInternal")

    # noinspection PyTypeChecker
    left_toolbar_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "left_toolbar_layout")
    left_toolbar_layout.addWidget(ConnectionWidget(window, app.get_heartbeat(), app))

    # Backlogs table
    backlogs_table: BacklogTableView = BacklogTableView(window, app, source, actions)
    backlogs_table.on(AfterSelectionChanged, lambda event, before, after: workitems_table.upstream_selected(after))
    backlogs_table.on(AfterSelectionChanged, lambda event, before, after: progress_widget.update_progress(after) if after is not None else None)
    left_layout.addWidget(backlogs_table)

    # Users table
    users_table: UserTableView = UserTableView(window, app, source, actions)
    left_layout.addWidget(users_table)

    # noinspection PyTypeChecker
    right_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rightTableLayoutInternal")

    # Workitems table
    workitems_table: WorkitemTableView = WorkitemTableView(window, app, source, actions)
    source.on(AfterWorkitemComplete, hide_timer)
    right_layout.addWidget(workitems_table)

    progress_widget = ProgressWidget(window, source)
    right_layout.addWidget(progress_widget)

    # noinspection PyTypeChecker
    search_bar: QtWidgets.QHBoxLayout = window.findChild(QtWidgets.QHBoxLayout, "searchBar")
    search = SearchBar(window, source, actions, backlogs_table, workitems_table)
    search_bar.addWidget(search)

    # noinspection PyTypeChecker
    root_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rootLayoutInternal")
    focus = FocusWidget(window, app, pomodoro_timer, source, settings, actions)
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

    # Toolbar
    # noinspection PyTypeChecker
    toolbar: QtWidgets.QToolBar = window.findChild(QtWidgets.QToolBar, "toolBar")
    if toolbar is not None:
        show_toolbar = (settings.get('Application.show_toolbar') == 'True')
        toolbar.setVisible(show_toolbar)

    # Tray icon
    show_tray_icon = (settings.get('Application.show_tray_icon') == 'True')
    tray = TrayIcon(window, pomodoro_timer, source, actions)
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
    tool_backlogs.setDefaultAction(action_backlogs)

    # noinspection PyTypeChecker
    tool_teams: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolTeams")
    tool_teams.setDefaultAction(action_teams)
    action_teams.setEnabled(settings.is_team_supported())
    tool_teams.setVisible(settings.is_team_supported())

    # noinspection PyTypeChecker
    tool_settings: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolSettings")
    tool_settings.clicked.connect(lambda: menu_file.exec(
        tool_settings.parentWidget().mapToGlobal(tool_settings.geometry().center())
    ))

    # Restore window config from settings
    update_tables_visibility()

    event_filter = ResizeEventFilter(window, main_layout, settings)
    window.installEventFilter(event_filter)
    window.move(app.primaryScreen().geometry().center() - window.frameGeometry().center())

    # Bind action domains to widget instances
    actions.bind('application', app)
    actions.bind('backlogs_table', backlogs_table)
    actions.bind('users_table', users_table)
    actions.bind('workitems_table', workitems_table)
    actions.bind('focus', focus)
    actions.bind('window', MainWindow())

    window.show()

    try:
        source.start()
    except Exception as ex:
        app.on_exception(type(ex), ex, ex.__traceback__)

    sys.exit(app.exec())

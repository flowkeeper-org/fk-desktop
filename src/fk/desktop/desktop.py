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

from PySide6 import QtCore, QtWidgets, QtUiTools
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox, QMainWindow, QMenu
from semantic_version import Version

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import AfterWorkitemComplete, SourceMessagesProcessed, TimerRestComplete, TimerWorkStart
from fk.core.timer import PomodoroTimer
from fk.core.timer_data import TimerData
from fk.core.workitem import Workitem
from fk.desktop.application import Application, AfterSourceChanged
from fk.desktop.config_wizard import ConfigWizard
from fk.desktop.tutorial import Tutorial
from fk.qt.abstract_tableview import AfterSelectionChanged
from fk.qt.actions import Actions
from fk.qt.audio_player import AudioPlayer
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.backlog_widget import BacklogWidget
from fk.qt.connection_widget import ConnectionWidget
from fk.qt.focus_widget import FocusWidget
from fk.qt.progress_widget import ProgressWidget
from fk.qt.qt_timer import QtTimer
from fk.qt.render.classic_timer_renderer import ClassicTimerRenderer
from fk.qt.render.minimal_timer_renderer import MinimalTimerRenderer
from fk.qt.resize_event_filter import ResizeEventFilter
from fk.qt.rest_fullscreen_widget import RestFullscreenWidget
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


def pin_if_needed(always_on_top_setting: str):
    window_was_visible = window.isVisible()
    focus_window_was_visible = focus_window.isVisible()

    is_pinned = always_on_top_setting == 'True'
    # Adding Qt.WindowType.WindowCloseButtonHint explicitly to fix #77
    window.setWindowFlags(window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint if is_pinned else
                          window.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowCloseButtonHint)
    focus_window.setWindowFlags(focus_window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint if is_pinned else
                                focus_window.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowCloseButtonHint)
    if window_was_visible:
        window.show()
    if focus_window_was_visible:
        focus_window.show()


def to_focus_mode(**kwargs) -> None:
    logger.debug('Switching to focus mode')

    was_already_hidden = window.isHidden()
    window.hide()
    root_layout.removeWidget(focus_widget)

    focus_widget.setParent(focus_window)
    focus_window.setCentralWidget(focus_widget)
    focus_window.setFixedWidth(focus_widget.width())
    focus_window.setFixedHeight(focus_widget.height())

    if was_already_hidden:
        # This must be due to hiding with --autostart. Make sure focus window has adequate size.
        logger.debug('Main window was already hidden when we entered focus mode.')
        focus_window.setFixedWidth(window.width())

    show_title = settings.get('Application.show_window_title') == 'True'
    focus_window.setWindowFlags(focus_window.windowFlags() & ~Qt.WindowType.FramelessWindowHint if show_title else
                                focus_window.windowFlags() | Qt.WindowType.FramelessWindowHint)
    focus_window.show()


def from_focus_mode(**_) -> None:
    logger.debug('Switching from focus mode')
    focus_window.hide()
    focus_widget.setParent(root_layout_widget)
    root_layout.insertWidget(0, focus_widget)
    window.show()


def update_tables_visibility() -> None:
    users_visible = (settings.get('Application.users_visible') == 'True')
    users_table.setVisible(users_visible)
    backlogs_visible = (settings.get('Application.backlogs_visible') == 'True')
    backlogs_widget.setVisible(backlogs_visible)
    left_table_layout.setVisible(users_visible or backlogs_visible)


def update_mode(timer_ticking: bool) -> None:
    mode = get_timer_ui_mode()
    if timer_ticking:
        if mode == 'focus':
            actions['window.focusMode'].setChecked(True)  # This will trigger to_focus_mode() automatically
        elif mode == 'minimize':
            window.hide()
    else:
        if mode == 'focus':
            actions['window.focusMode'].setChecked(False)  # This will trigger from_focus_mode() automatically
        elif mode == 'minimize':
            # It's a bit more complex than just showing the main window, because the user might have
            # detached the focus widget in the meantime.
            if focus_widget.parent() == focus_window:
                actions['window.focusMode'].setChecked(False)  # This will trigger from_focus_mode() automatically
            elif focus_widget.parent() == root_layout_widget:
                window.show()
            else:
                raise Exception("Focus widget is detached, this should never happen. Please open a bug in GitHub.")


def recreate_tray_icon(flavor: str, show_tray_icon_setting: str) -> None:
    global tray
    initialize_timer = False
    if tray is not None:
        tray.kill()
        tray.setVisible(False)
        initialize_timer = True
    tray = TrayIcon(window,
                    pomodoro_timer,
                    app.get_source_holder(),
                    actions,
                    48,
                    MinimalTimerRenderer if 'thin' in flavor else ClassicTimerRenderer,
                    'dark' in flavor)
    if initialize_timer:
        tray.initialized()
    tray.setVisible(show_tray_icon_setting == 'True')


def on_settings_changed(event: str, old_values: dict[str, str], new_values: dict[str, str]):
    logger.debug(f'Settings changed from {old_values} to {new_values}')
    status.showMessage('Settings changed')

    backlogs_visible = None
    users_visible = None

    for name in new_values.keys():
        new_value = new_values[name]
        if name == 'Application.show_main_menu':
            main_menu.setVisible(new_value == 'True')
        elif name == 'Application.show_status_bar':
            status.setVisible(new_value == 'True')
        elif name == 'Application.show_left_toolbar':
            left_toolbar.setVisible(new_value == 'True')
        elif name == 'Application.show_tray_icon':
            tray.setVisible(new_value == 'True')
        elif name == 'Application.shortcuts':
            actions.update_from_settings(new_value)
        elif name == 'Application.always_on_top':
            pin_if_needed(new_value)
        elif name == 'Application.focus_flavor':
            focus_widget.set_flavor(new_value)
        elif name == 'RestScreen.flavor':
            rest_fullscreen_widget.set_flavor(new_value)
        elif name == 'Application.tray_icon_flavor':
            recreate_tray_icon(new_value,
                               new_values.get('Application.show_tray_icon',
                                              settings.get('Application.show_tray_icon')))
        elif name == 'Application.backlogs_visible':
            backlogs_visible = new_value == 'True'
            backlogs_widget.setVisible(backlogs_visible)
        elif name == 'Application.users_visible':
            users_visible = new_value == 'True'
            users_table.setVisible(users_visible)

    if backlogs_visible is not None or users_visible is not None:
        left_table_layout.setVisible((users_visible is not None and users_visible) or (backlogs_visible is not None and backlogs_visible))


class MainWindow:
    def __init__(self):
        super().__init__()

    def toggle_focus_mode(self, state: bool):
        if state:
            to_focus_mode()
        else:
            from_focus_mode()

    def toggle_pin_window(self, state: bool):
        is_checked: bool = actions['window.pinWindow'].isChecked()
        settings.set({'Application.always_on_top': str(is_checked)})

    def toggle_main_window(self):
        if window.isVisible():
            # If main window is visible, then focus widget must be in it,
            # then it's enough to just hide the main window
            window.hide()
        else:
            if focus_window.isVisible():
                # We are in the focus mode -- hide focus window. The main window is already hidden.
                focus_window.hide()
            else:
                # Everything is hidden. We need to detect the mode before showing correct window.
                # We do it by checking focus widget's parent.
                if focus_widget.parent() == focus_window:
                    focus_window.show()
                elif focus_widget.parent() == root_layout_widget:
                    window.show()
                else:
                    raise Exception("Focus widget is detached, this should never happen. Please open a bug in GitHub.")

    def show_search(self):
        search.show()

    def show_tutorial(self):
        global tutorial
        tutorial = Tutorial(app.get_source_holder(), settings, window, focus_window)

    def on_upgrade(self, from_version: Version):
        if from_version.major == 0 and from_version.minor < 9:
            if window.isHidden() and focus_window.isHidden():
                # Even if it was configured to hide, typically thanks to --autostart
                window.show()
            wizard = ConfigWizard(app, actions, window)
            wizard.closed.connect(self.show_tutorial)
            wizard.show()

    def toggle_backlogs(self, enabled):
        settings.set({'Application.backlogs_visible': str(enabled)})

    def toggle_users(self, enabled):
        settings.set({'Application.users_visible': str(enabled)})

    @staticmethod
    def define_actions(actions: Actions):
        actions.add('window.focusMode', "Focus Mode", None, ("tool-show-timer-only", "tool-show-all"), MainWindow.toggle_focus_mode, True)
        actions.add('window.pinWindow', "Pin Flowkeeper", None, "tool-pin", MainWindow.toggle_pin_window, True)
        actions.add('window.showMainWindow', "Show / Hide Main Window", None, "tool-show-timer-only", MainWindow.toggle_main_window)
        actions.add('window.showSearch', "Search...", 'Ctrl+F', '', MainWindow.show_search)

        backlogs_were_visible = (actions.get_settings().get('Application.backlogs_visible') == 'True')
        actions.add('window.showBacklogs',
                    "Show / Hide Backlogs",
                    'Ctrl+B',
                    ('tool-left-close', 'tool-left-open'),
                    MainWindow.toggle_backlogs,
                    True,
                    backlogs_were_visible)

        users_were_visible = (actions.get_settings().get('Application.users_visible') == 'True')
        actions.add('window.showUsers',
                    "Team",
                    'Ctrl+T',
                    'tool-teams',
                    MainWindow.toggle_users,
                    True,
                    actions.get_settings().is_team_supported() and users_were_visible)


if __name__ == "__main__":
    # The order is important here. Some Sources use Qt APIs, so we need an Application instance created first.
    # Then we initialize a Source. This needs to happen before we configure UI, because the Source will replay
    # Strategies in __init__, and we don't want anyone to be subscribed to their events yet. It will build the
    # data model. Once the Source is constructed, we can initialize the rest of the UI, including Qt data models.
    # From that moment we can respond to user actions and events from the backend, which the Source + Strategies
    # will pass through to Qt data models via Qt-like connect / emit mechanism.
    try:
        app = Application(sys.argv)
        settings = app.get_settings()

        logger.debug(f'UI thread: {threading.get_ident()}')
        settings.on(events.AfterSettingsChanged, on_settings_changed)

        def _on_workitem_complete(workitem: Workitem, timer: TimerData):
            if timer.get_running_workitem() == workitem:
                update_mode(False)

        def _on_source_changed(event: str, source: AbstractEventSource):
            actions['window.focusMode'].setChecked(False)
            source.on(SourceMessagesProcessed, lambda **_: update_mode(source.get_data().get_current_user().get_timer().is_ticking()), last=True)
            source.on(AfterWorkitemComplete, lambda workitem, **_: _on_workitem_complete(workitem, source.get_data().get_current_user().get_timer()), last=True)
            source.on(TimerRestComplete, lambda **_: update_mode(False))
            source.on(TimerWorkStart, lambda **_: update_mode(True))

        app.get_source_holder().on(AfterSourceChanged, _on_source_changed)

        pomodoro_timer = PomodoroTimer(QtTimer("Pomodoro Tick"),
                                       QtTimer("Pomodoro Transition"),
                                       app.get_settings(),
                                       app.get_source_holder())

        loader = QtUiTools.QUiLoader(app)

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
        actions.all_actions_defined()

        audio = AudioPlayer(window, app.get_source_holder(), settings)

        # File menu
        menu_file = QtWidgets.QMenu("File", window)
        menu_file.addAction(actions['application.settings'])
        menu_file.addAction(actions['application.import'])
        menu_file.addAction(actions['application.export'])
        menu_file.addAction(actions['application.stats'])
        menu_file.addAction(actions['application.workSummary'])
        menu_file.addSeparator()

        menu_contact = QtWidgets.QMenu("Contact us", window)
        menu_contact.addAction(actions['application.contactGithub'])
        menu_contact.addAction(actions['application.contactDiscord'])
        menu_contact.addAction(actions['application.contactLinkedIn'])
        menu_contact.addAction(actions['application.contactReddit'])
        menu_contact.addAction(actions['application.contactTelegram'])
        menu_contact.addAction(actions['application.contactEmail'])
        menu_file.addMenu(menu_contact)

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
        backlogs_widget.get_tags().on(AfterSelectionChanged, lambda event, before, after: workitems_widget.upstream_selected(after))
        backlogs_widget.get_table().on(AfterSelectionChanged, lambda event, before, after: progress_widget.update_progress(after) if after is not None else None)
        backlogs_widget.get_tags().on(AfterSelectionChanged, lambda event, before, after: progress_widget.update_progress(after) if after is not None else None)
        left_layout.addWidget(backlogs_widget)

        # Users table
        users_table: UserTableView = UserTableView(window, app, app.get_source_holder(), actions)
        left_layout.addWidget(users_table)

        # noinspection PyTypeChecker
        right_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rightTableLayoutInternal")

        # Workitems table
        workitems_widget: WorkitemWidget = WorkitemWidget(window,
                                                          app,
                                                          app.get_source_holder(),
                                                          pomodoro_timer,
                                                          actions)
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
        root_layout_widget: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "rootLayout")

        focus_window = QMainWindow(window)
        focus_window.addActions(list(actions.values()))

        # noinspection PyTypeChecker
        root_layout: QtWidgets.QVBoxLayout = window.findChild(QtWidgets.QVBoxLayout, "rootLayoutInternal")
        focus_widget = FocusWidget(root_layout_widget,
                                   app,
                                   pomodoro_timer,
                                   app.get_source_holder(),
                                   settings,
                                   actions,
                                   settings.get('Application.focus_flavor'))
        root_layout.insertWidget(0, focus_widget)

        # Focus window should keep the same title as the main one
        focus_window.setWindowTitle(window.windowTitle())
        window.windowTitleChanged.connect(focus_window.setWindowTitle)

        # Create the fullscreen rest widget
        rest_fullscreen_widget = RestFullscreenWidget(window,
                                                     app,
                                                     pomodoro_timer,
                                                     app.get_source_holder(),
                                                     settings,
                                                      settings.get('RestScreen.flavor'))

        # Layouts
        # noinspection PyTypeChecker
        main_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "mainLayout")
        # noinspection PyTypeChecker
        left_table_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "leftTableLayout")

        # noinspection PyTypeChecker
        action_backlogs = actions['window.showBacklogs']
        action_teams = actions['window.showUsers']

        # Main menu
        # noinspection PyTypeChecker
        main_menu: QtWidgets.QMenuBar = window.findChild(QtWidgets.QMenuBar, "menuBar")
        # Application.define_actions(actions)
        # BacklogTableView.define_actions(actions)
        # UserTableView.define_actions(actions)
        # WorkitemTableView.define_actions(actions)
        # FocusWidget.define_actions(actions)
        # MainWindow.define_actions(actions)
        if main_menu is not None:
            main_menu.addMenu(menu_file)
            view_menu = QMenu('View', main_menu)
            view_menu.addAction(actions['window.focusMode'])
            view_menu.addAction(actions['window.pinWindow'])
            view_menu.addAction(actions['window.showBacklogs'])
            view_menu.addAction(actions['application.toolbar'])
            view_menu.addSeparator()
            view_menu.addAction(actions['workitems_table.hideCompleted'])
            view_menu.addAction(actions['window.showSearch'])
            main_menu.addMenu(view_menu)
            backlogs_menu = QMenu('Backlogs', main_menu)
            backlogs_menu.addAction(actions['backlogs_table.newBacklog'])
            backlogs_menu.addAction(actions['backlogs_table.newBacklogFromIncomplete'])
            backlogs_menu.addAction(actions['backlogs_table.renameBacklog'])
            backlogs_menu.addAction(actions['backlogs_table.deleteBacklog'])
            main_menu.addMenu(backlogs_menu)
            workitems_menu = QMenu('Work items', main_menu)
            workitems_menu.addAction(actions['workitems_table.newItem'])
            workitems_menu.addAction(actions['workitems_table.renameItem'])
            workitems_menu.addAction(actions['workitems_table.deleteItem'])
            workitems_menu.addAction(actions['workitems_table.startItem'])
            workitems_menu.addAction(actions['workitems_table.completeItem'])
            workitems_menu.addSeparator()
            workitems_menu.addAction(actions['workitems_table.addPomodoro'])
            workitems_menu.addAction(actions['workitems_table.removePomodoro'])
            workitems_menu.addAction(actions['focus.voidPomodoro'])
            workitems_menu.addAction(actions['focus.finishTracking'])
            main_menu.addMenu(workitems_menu)
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
        tray: TrayIcon | None = None
        recreate_tray_icon(settings.get('Application.tray_icon_flavor'), settings.get('Application.show_tray_icon'))

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
        tool_settings.setIcon(QIcon.fromTheme('tool-settings'))
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
        app.upgraded.connect(main_window.on_upgrade)

        # Bind action domains to widget instances
        actions.bind('application', app)
        actions.bind('backlogs_table', backlogs_widget.get_table())
        actions.bind('users_table', users_table)
        actions.bind('workitems_table', workitems_widget.get_table())
        actions.bind('focus', focus_widget)
        actions.bind('window', main_window)

        pin_if_needed(settings.get('Application.always_on_top'))

        tutorial: Tutorial = None

        if not app.is_hide_on_start():
            window.show()

        # With Qt 6.7.1 on Windows this needs to happen AFTER the Window is shown.
        # Otherwise, the font size for the focus' header is picked correctly, but
        # default font family is used.
        focus_widget.update_fonts()
        rest_fullscreen_widget.update_fonts()

        try:
            app.initialize_source()
        except Exception as ex:
            app.on_exception(type(ex), ex, ex.__traceback__)

        if app.is_e2e_mode():
            # Our end-to-end tests use asyncio.sleep() extensively, so we need Qt event loop to support coroutines.
            # This is an experimental feature in Qt 6.6.2+.
            from PySide6 import QtAsyncio
            QtAsyncio.run()
        else:
            if '--reset' in app.arguments():
                settings.reset_to_defaults()
            # This would work on any Qt 6.6.x
            code = app.exec()
            if tray is not None and tray.isVisible():
                # To avoid tray icon getting stuck on Windows
                tray.hide()
            sys.exit(code)

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

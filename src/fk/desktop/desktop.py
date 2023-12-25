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
import sys
from typing import Iterable

from PySide6 import QtCore, QtWidgets, QtUiTools, QtGui, QtMultimedia
from PySide6.QtCore import QItemSelection

from fk.core import events
from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.app import App
from fk.core.backlog import Backlog
from fk.core.backlog_strategies import DeleteBacklogStrategy, CreateBacklogStrategy
from fk.core.events import SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.pomodoro_strategies import AddPomodoroStrategy, RemovePomodoroStrategy, CompletePomodoroStrategy, \
    StartWorkStrategy
from fk.core.timer import PomodoroTimer
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import DeleteWorkitemStrategy, CreateWorkitemStrategy, CompleteWorkitemStrategy
from fk.desktop.application import Application
from fk.desktop.export_wizard import ExportWizard
from fk.desktop.import_wizard import ImportWizard
from fk.desktop.settings import SettingsDialog
from fk.qt.backlog_model import BacklogModel
from fk.qt.pomodoro_delegate import PomodoroDelegate
from fk.qt.qt_filesystem_watcher import QtFilesystemWatcher
from fk.qt.qt_timer import QtTimer
from fk.qt.search_completer import SearchBar
from fk.qt.timer_widget import render_for_widget, render_for_pixmap, TimerWidget
from fk.qt.user_model import UserModel
from fk.qt.websocket_event_source import WebsocketEventSource
from fk.qt.workitem_model import WorkitemModel


#from fk.qt.websocket_event_source import WebsocketEventSource


def _get_selected(table: QtWidgets.QTableView) -> Backlog | Workitem:
    index = _get_selected_index(table)
    if index is not None:
        return index.data(500)


def _get_selected_index(table: QtWidgets.QTableView) -> QtCore.QModelIndex:
    model: QtCore.QItemSelectionModel = table.selectionModel()
    if model is not None:
        indexes = model.selectedIndexes()
        if len(indexes) == 1:
            return indexes[0]   # Backlogs case
        elif len(indexes) == 3:
            return indexes[1]   # Workitems case


def get_selected_backlog() -> Backlog:
    return _get_selected(backlogs_table)


def get_selected_workitem() -> Workitem:
    return _get_selected(workitems_table)


def enable_workitem_actions(enable: bool) -> None:
    action_delete_workitem.setEnabled(enable)
    action_complete_workitem.setEnabled(enable)
    action_rename_workitem.setEnabled(enable)
    action_start.setEnabled(enable)
    action_add_pomodoro.setEnabled(enable)
    action_remove_pomodoro.setEnabled(enable)


def update_progress(backlog: Backlog) -> None:
    total: int = 0
    done: int = 0
    for wi in backlog.values():
        for p in wi.values():
            total += 1
            if p.is_finished() or p.is_canceled():
                done += 1

    backlog_progress.setVisible(total > 0)
    backlog_progress.setMaximum(total)
    backlog_progress.setValue(done)
    backlog_progress_txt.setVisible(total > 0)
    backlog_progress_txt.setText(f'{done} of {total} done')


def backlog_changed(selected: QItemSelection) -> None:
    backlog: Backlog | None = None
    if selected.data():
        backlog = selected.data().topLeft().data(500)
        workitem_model.load(backlog)
        update_progress(backlog)

    # It can be None if we don't have any backlogs left. BacklogModel supports None.
    enabled = backlog is not None
    action_delete_backlog.setEnabled(enabled)
    action_rename_backlog.setEnabled(enabled)

    # None of the workitems is selected now
    action_new_workitem.setEnabled(enabled)
    enable_workitem_actions(False)

    # This only works if we have some data there
    workitems_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    workitems_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
    workitems_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)


def load_backlogs() -> None:
    backlog_model.load()
    backlogs_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)


def load_users() -> None:
    user_model.load()
    users_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)


def workitem_changed(selected: QtCore.QModelIndex) -> None:
    if selected.data():
        workitem = selected.data().topLeft().data(500)
        enable_workitem_actions(not workitem.is_sealed())
    else:
        enable_workitem_actions(False)


def tray_clicked() -> None:
    if continue_workitem is not None:
        # TODO Start THAT workitem
        start_work()
    else:
        if window.isHidden():
            window.show()
        else:
            window.hide()


def delete_backlog() -> None:
    selected: Backlog = get_selected_backlog()
    if selected is not None:
        m = QtWidgets.QMessageBox()
        if m.warning(window,
                     "Confirmation",
                     f"Are you sure you want to delete backlog '{selected.get_name()}'?",
                     QtWidgets.QMessageBox.StandardButton.Ok,
                     QtWidgets.QMessageBox.StandardButton.Cancel
                     ) == QtWidgets.QMessageBox.StandardButton.Ok:
            source.execute(DeleteBacklogStrategy, [selected.get_uid()])
            enable_workitem_actions(False)


def delete_workitem() -> None:
    selected: Workitem = get_selected_workitem()
    if selected is not None:
        m = QtWidgets.QMessageBox()
        if m.warning(window,
                     "Confirmation",
                     f"Are you sure you want to delete workitem '{selected.get_name()}'?",
                     QtWidgets.QMessageBox.StandardButton.Ok,
                     QtWidgets.QMessageBox.StandardButton.Cancel
                     ) == QtWidgets.QMessageBox.StandardButton.Ok:
            source.execute(DeleteWorkitemStrategy, [selected.get_uid()])
            enable_workitem_actions(False)  # Just in case


def add_pomodoro() -> None:
    selected: Workitem = get_selected_workitem()
    if selected is not None:
        source.execute(AddPomodoroStrategy, [selected.get_uid(), "1"])


def remove_pomodoro() -> None:
    selected: Workitem = get_selected_workitem()
    if selected is not None:
        source.execute(RemovePomodoroStrategy, [selected.get_uid(), "1"])


def generate_unique_name(prefix: str, parent: Iterable) -> str:
    check = prefix
    n = 1
    while check in parent:
        check = f"{prefix} {n}"
        n += 1
    return check


def create_backlog() -> None:
    prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
    new_name = generate_unique_name(prefix, source.backlogs())
    source.execute(CreateBacklogStrategy, [generate_uid(), new_name])

    # Start editing it. The new item will always be at the top of the list.
    index: QtCore.QModelIndex = backlog_model.index(0, 0)
    backlogs_table.setCurrentIndex(index)
    backlogs_table.edit(index)


def create_workitem() -> None:
    backlog: Backlog = get_selected_backlog()
    if backlog is not None:
        new_name = generate_unique_name("Do something", backlog)
        source.execute(CreateWorkitemStrategy, [generate_uid(), backlog.get_uid(), new_name])

        # Start editing it. The new item will always be at the end of the list.
        index: QtCore.QModelIndex = workitem_model.index(workitem_model.rowCount() - 1, 1)
        workitems_table.setCurrentIndex(index)
        workitems_table.edit(index)


def rename_backlog() -> None:
    index: QtCore.QModelIndex = _get_selected_index(backlogs_table)
    if index is not None:
        backlogs_table.edit(index)


def rename_workitem() -> None:
    index: QtCore.QModelIndex = _get_selected_index(workitems_table)
    if index is not None:
        workitems_table.edit(index)


def start_work() -> None:
    workitem: Workitem = get_selected_workitem()
    # TODO: This is where we can adjust work duration
    # TODO: Move this to Timer and adjust rest, too
    source.execute(StartWorkStrategy, [workitem.get_uid(), str(get_work_duration())])


def complete_work() -> None:
    workitem: Workitem = get_selected_workitem()
    if not workitem.has_running_pomodoro() or QtWidgets.QMessageBox().warning(window,
            "Confirmation",
            f"Are you sure you want to complete current workitem? This will void current pomodoro.",
            QtWidgets.QMessageBox.StandardButton.Ok,
            QtWidgets.QMessageBox.StandardButton.Cancel
            ) == QtWidgets.QMessageBox.StandardButton.Ok:
        source.execute(CompleteWorkitemStrategy, [workitem.get_uid(), "finished"])
        hide_timer()
        tool_next.hide()
        tool_complete.hide()
        update_header(pomodoro_timer)


def get_work_duration() -> int:
    return int(settings.get('Pomodoro.default_work_duration'))


# Unlike work duration, we only use it for the settings window here.
# TODO - move this logic into the settings module
def get_rest_duration() -> int:
    return int(settings.get('Pomodoro.default_rest_duration'))


def paint_timer_in_tray() -> None:
    tray_width = 48
    tray_height = 48
    pixmap = QtGui.QPixmap(tray_width, tray_height)
    pixmap.fill(QtGui.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    timer_tray.repaint(painter, QtCore.QRect(0, 0, tray_width, tray_height))
    tray.setIcon(pixmap)


def show_notification(event: str = None, **kwargs) -> None:
    # Tray notification
    if event == 'TimerWorkComplete':
        tray.showMessage("Work is done", "Have some rest", default_icon)
    elif event == 'TimerRestComplete':
        icon = default_icon
        w = kwargs.get('workitem')
        if w is not None and w.is_startable():
            icon = next_icon
        tray.showMessage("Ready", "Start a new pomodoro", icon)

    # Alarm bell
    play_alarm_sound = (settings.get('Application.play_alarm_sound') == 'True')
    play_rest_sound = (settings.get('Application.play_rest_sound') == 'True')
    if play_alarm_sound and (event == 'TimerRestComplete' or not play_rest_sound):
        audio_player.stop()     # In case it was ticking or playing rest music
        alarm_file = settings.get('Application.alarm_sound_file')
        reset_audio()
        audio_player.setSource(alarm_file)
        audio_player.setLoops(1)
        audio_player.play()

    # Rest music
    if event == 'TimerWorkComplete':
        start_rest_sound()


def start_ticking(timer: PomodoroTimer = None, event: str = None) -> None:
    play_tick_sound = (settings.get('Application.play_tick_sound') == 'True')
    if play_tick_sound:
        audio_player.stop()     # Just in case
        tick_file = settings.get('Application.tick_sound_file')
        reset_audio()
        print(f'Will tick: {tick_file}')
        audio_player.setSource(tick_file)
        audio_player.setLoops(QtMultimedia.QMediaPlayer.Loops.Infinite)
        audio_player.play()


def start_rest_sound() -> None:
    play_rest_sound = (settings.get('Application.play_rest_sound') == 'True')
    if play_rest_sound:
        audio_player.stop()     # In case it was ticking
        rest_file = settings.get('Application.rest_sound_file')
        reset_audio()
        audio_player.setSource(rest_file)
        audio_player.setLoops(1)
        audio_player.play()     # This will substitute the bell sound


def get_timer_ui_mode() -> str:
    # Options: keep (don't do anything), focus (collapse main layout), minimize (window to tray)
    return settings.get('Application.timer_ui_mode')


def show_timer() -> None:
    header_layout.show()
    main_layout.hide()
    left_toolbar.hide()
    window.setMaximumHeight(header_layout.size().height())
    window.setMinimumHeight(header_layout.size().height())
    tool_show_timer_only.hide()
    tool_show_all.show()


def show_timer_automatically() -> None:
    global continue_workitem
    action_void.setEnabled(True)
    continue_workitem = None
    mode = get_timer_ui_mode()
    if mode == 'focus':
        show_timer()
    elif mode == 'minimize':
        window.hide()


def hide_timer() -> None:
    main_layout.show()
    header_layout.show()
    left_toolbar.show()
    window.setMaximumHeight(16777215)
    window.setMinimumHeight(0)
    tool_show_timer_only.show()
    tool_show_all.hide()
    restore_size()


def hide_timer_automatically(workitem) -> None:
    global continue_workitem

    action_void.setDisabled(True)

    # Show "Next" icon if there's pomodoros remaining
    if workitem is not None and workitem.is_startable():
        continue_workitem = workitem
        # TODO Show "Complete" button here, too
        tool_next.show()
        tool_complete.show()
        next_in_tray_icon()
        return

    continue_workitem = None
    tool_next.hide()
    tool_complete.hide()
    reset_tray_icon()

    mode = get_timer_ui_mode()
    if mode == 'focus':
        hide_timer()
    elif mode == 'minimize':
        window.show()


def update_header(timer: PomodoroTimer, **kwargs) -> None:
    running_workitem: Workitem = timer.get_running_workitem()
    if timer.is_idling():
        w = kwargs.get('workitem')  # != running_workitem for end-of-pomodoro
        if w is not None and w.is_startable():
            header_text.setText('Start another Pomodoro?')
            header_subtext.setText(w.get_name())
            tray.setToolTip(f'Start another Pomodoro? ({w.get_name()})')
        else:
            header_text.setText('Idle')
            header_subtext.setText("It's time for the next Pomodoro.")
            tray.setToolTip("It's time for the next Pomodoro.")
        tool_void.hide()
        timer_display.set_values(0, None, "")
        timer_display.hide()
    elif timer.is_working() or timer.is_resting():
        remaining_duration = timer.get_remaining_duration()     # This is always >= 0
        remaining_minutes = str(int(remaining_duration / 60)).zfill(2)
        remaining_seconds = str(int(remaining_duration % 60)).zfill(2)
        state = 'Focus' if timer.is_working() else 'Rest'
        txt = f'{state}: {remaining_minutes}:{remaining_seconds}'
        header_text.setText(f'{txt} left')
        header_subtext.setText(running_workitem.get_name())
        tray.setToolTip(f"{txt} left ({running_workitem.get_name()})")
        tool_void.show()
        tool_next.hide()
        tool_complete.hide()
        timer_display.set_values(
            remaining_duration / timer.get_planned_duration(),
            None,
            ""  # f'{remaining_minutes}:{remaining_seconds}'
        )
        timer_tray.set_values(
            remaining_duration / timer.get_planned_duration(),
        )
        paint_timer_in_tray()
        timer_display.show()
    else:
        raise Exception("The timer is in an unexpected state")
    timer_display.repaint()


def auto_resize() -> None:
    h: int = QtGui.QFontMetrics(QtGui.QFont()).height() + 8
    users_table.verticalHeader().setDefaultSectionSize(h)
    backlogs_table.verticalHeader().setDefaultSectionSize(h)
    workitems_table.verticalHeader().setDefaultSectionSize(h)
    # Save it to Settings, so that we can use this value when
    # calculating display hints for the Pomodoro Delegate.
    # As of now, this requires app restart to apply.
    settings.set('Application.table_row_height', str(h))


def restore_size() -> None:
    w = int(settings.get('Application.window_width'))
    h = int(settings.get('Application.window_height'))
    splitter_width = int(settings.get('Application.window_splitter_width'))
    splitter.setSizes([splitter_width, w - splitter_width])
    window.resize(QtCore.QSize(w, h))


def save_splitter_size(new_width: int, index: int) -> None:
    old_width = int(settings.get('Application.window_splitter_width'))
    if old_width != new_width:
        settings.set('Application.window_splitter_width', str(new_width))
        #print(f"Saved new splitter width {new_width}")


class MainWindowEventFilter(QtWidgets.QMainWindow):
    _window: QtWidgets.QMainWindow
    _timer: QtTimer
    _is_resizing: bool

    def __init__(self, window: QtWidgets.QMainWindow):
        super().__init__()
        self._window = window
        self._timer = QtTimer()
        self._is_resizing = False

    def resize_completed(self):
        self._is_resizing = False
        if not main_layout.isVisible():  # Avoid saving window size in Timer mode
            return
        # We'll check against the old value to avoid resize loops and spurious setting change events
        new_width = self._window.size().width()
        new_height = self._window.size().height()
        old_width = int(settings.get('Application.window_width'))
        old_height = int(settings.get('Application.window_height'))
        if old_width != new_width or old_height != new_height:
            settings.set('Application.window_width', str(new_width))
            settings.set('Application.window_height', str(new_height))
            #print(f"Saved new window size {new_width} x {new_height}")

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize and isinstance(event, QtGui.QResizeEvent):
            if widget == self._window:
                if self._is_resizing:   # Don't fire those events too frequently
                    return False
                self._timer.schedule(1000,
                                     lambda _: self.resize_completed(),
                                     None,
                                     True)
                self._is_resizing = True
        return False


def note_pomodoro() -> None:
    global notes
    (new_notes, ok) = QtWidgets.QInputDialog.getMultiLineText(window,
                                                              "Interruption",
                                                              "Take your notes here:",
                                                              notes)
    if ok:
        notes = new_notes


def void_pomodoro() -> None:
    for backlog in source.backlogs():
        workitem, _ = backlog.get_running_workitem()
        if workitem is not None:
            if QtWidgets.QMessageBox().warning(window,
                         "Confirmation",
                         f"Are you sure you want to void current pomodoro?",
                         QtWidgets.QMessageBox.StandardButton.Ok,
                         QtWidgets.QMessageBox.StandardButton.Cancel
                         ) == QtWidgets.QMessageBox.StandardButton.Ok:
                source.execute(CompletePomodoroStrategy, [workitem.get_uid(), "canceled"])


def reset_tray_icon() -> None:
    tray.setIcon(default_icon)


def next_in_tray_icon() -> None:
    tray.setIcon(next_icon)


def initialize_fonts(s: AbstractSettings) -> (QtGui.QFont, QtGui.QFont, QtGui.QFont, QtGui.QFont):
    font_header = QtGui.QFont(s.get('Application.font_header_family'),
                              int(s.get('Application.font_header_size')))
    if font_header is None:
        font_header = QtGui.QFont()
        font_header.setPointSize(int(font_header.pointSize() * 24.0 / 9))

    font_main = QtGui.QFont(s.get('Application.font_main_family'),
                            int(s.get('Application.font_main_size')))
    if font_main is None:
        font_main = QtGui.QFont()

    app.setFont(font_main)
    backlogs_table.setFont(font_main)  # Even though we set it on the App level, Windows just ignores it
    users_table.setFont(font_main)
    workitems_table.setFont(font_main)
    header_text.setFont(font_header)

    auto_resize()


def toggle_backlogs(visible) -> None:
    backlogs_table.setVisible(visible)
    left_table_layout.setVisible(visible or users_table.isVisible())


def toggle_show_completed_workitems(checked) -> None:
    workitem_model.show_completed(checked)
    search.show_completed(checked)
    workitems_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
    workitems_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
    workitems_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)


def toggle_users(visible) -> None:
    users_table.setVisible(visible)
    left_table_layout.setVisible(backlogs_table.isVisible() or visible)


def on_messages(event: str = None) -> None:
    global replay_completed
    global timer_tray
    global timer_display
    global pomodoro_timer

    if replay_completed:
        return
    replay_completed = True

    print('Replay completed')

    load_backlogs()
    load_users()

    # Timer
    # noinspection PyTypeChecker
    timer_widget: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "timer")
    timer_display = render_for_widget(
        window.palette(),
        timer_widget,
        QtGui.QFont(),
        0.3
    )
    timer_tray = render_for_pixmap()

    pomodoro_timer = PomodoroTimer(source, QtTimer(), QtTimer())
    pomodoro_timer.connect("Timer*", update_header)
    pomodoro_timer.connect("Timer*Complete", show_notification)
    pomodoro_timer.connect("TimerWorkStart", start_ticking)
    pomodoro_timer.connect("TimerRestComplete", lambda timer, workitem, pomodoro, event: hide_timer_automatically(workitem))
    pomodoro_timer.connect("TimerWorkStart", lambda timer, event: show_timer_automatically())
    update_header(pomodoro_timer)

    # It's important to do it after window.show() above
    if pomodoro_timer.is_working():
        start_ticking()
        show_timer_automatically()
    elif pomodoro_timer.is_resting():
        start_rest_sound()
        show_timer_automatically()


def reset_audio():
    global audio_output
    global audio_player
    audio_output = QtMultimedia.QAudioOutput()
    audio_player = QtMultimedia.QMediaPlayer(app)
    audio_player.setAudioOutput(audio_output)


def eye_candy():
    header_bg = settings.get('Application.header_background')
    if header_bg:
        window.setStyleSheet(f"#headerLayout {{ background: url('{header_bg}') center fit; }}")
    else:
        window.setStyleSheet(f"#headerLayout {{ background: none; }}")


def restart_warning() -> None:
    QtWidgets.QMessageBox().warning(window,
                                    "Restart required",
                                    f"Please restart Flowkeeper to apply new settings",
                                    QtWidgets.QMessageBox.StandardButton.Ok)


def on_setting_changed(event: str, name: str, old_value: str, new_value: str):
    # print(f'Setting {name} changed from {old_value} to {new_value}')
    status.showMessage('Settings changed')
    if name == 'Source.type':
        restart_warning()
    elif name == 'Application.timer_ui_mode' and (pomodoro_timer.is_working() or pomodoro_timer.is_resting()):
        # TODO: This really doesn't work well
        hide_timer_automatically(None)
        show_timer_automatically()
    elif name == 'Application.quit_on_close':
        app.setQuitOnLastWindowClosed(new_value == 'True')
    elif 'Application.font_' in name:
        initialize_fonts(settings)
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
    elif name == 'Application.header_background':
        eye_candy()
    elif name == 'Application.theme':
        restart_warning()
        # app.set_theme(new_value)
    # TODO: Subscribe to sound settings
    # TODO: Subscribe the sources to the settings they use
    # TODO: Reload the app when the source changes


def export():
    wizard = ExportWizard(source, window)
    wizard.show()


def import_():
    wizard = ImportWizard(source, window)
    wizard.show()


def show_about():
    # noinspection PyTypeChecker
    about_version: QtWidgets.QLabel = about_window.findChild(QtWidgets.QLabel, "version")
    file = QtCore.QFile(":/VERSION.txt")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    about_version.setText(file.readAll().toStdString())
    file.close()

    # noinspection PyTypeChecker
    about_changelog: QtWidgets.QTextEdit = about_window.findChild(QtWidgets.QTextEdit, "notes")
    file = QtCore.QFile(":/CHANGELOG.txt")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    about_changelog.setText(file.readAll().toStdString())
    file.close()

    # noinspection PyTypeChecker
    about_credits: QtWidgets.QTextEdit = about_window.findChild(QtWidgets.QTextEdit, "credits")
    file = QtCore.QFile(":/CREDITS.txt")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    about_credits.setText(file.readAll().toStdString())
    file.close()

    # noinspection PyTypeChecker
    about_license: QtWidgets.QTextEdit = about_window.findChild(QtWidgets.QTextEdit, "license")
    file = QtCore.QFile(":/LICENSE.txt")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    about_license.setText(file.readAll().toStdString())
    file.close()

    about_window.show()


# The order is important here. Some Sources use Qt APIs, so we need an Application instance created first.
# Then we initialize a Source. This needs to happen before we configure UI, because the Source will replay
# Strategies in __init__, and we don't want anyone to be subscribed to their events yet. It will build the
# data model. Once the Source is constructed, we can initialize the rest of the UI, including Qt data models.
# From that moment we can respond to user actions and events from the backend, which the Source + Strategies
# will pass through to Qt data models via Qt-like connect / emit mechanism.
app = Application(sys.argv)
settings = app.get_settings()
settings.connect(events.AfterSettingChanged, on_setting_changed)

notes = ""

replay_completed = False
timer_tray: TimerWidget | None = None
timer_display: TimerWidget | None = None

default_icon = QtGui.QIcon(":/icons/logo.png")
next_icon = QtGui.QIcon(":/icons/tool-next.svg")

#print(QtWidgets.QStyleFactory.keys())
#app.setStyle(QtWidgets.QStyleFactory.create("Windows"))

audio_output = QtMultimedia.QAudioOutput()
audio_player = QtMultimedia.QMediaPlayer(app)
audio_player.setAudioOutput(audio_output)

source: AbstractEventSource
source_type = settings.get('Source.type')
root = App(settings)
if source_type == 'local':
    source = FileEventSource(settings, root, QtFilesystemWatcher())
elif source_type in ('websocket', 'flowkeeper.org', 'flowkeeper.pro'):
    source = WebsocketEventSource(settings, root)
else:
    raise Exception(f"Source type {source_type} not supported")

data = source.get_data()
source.connect(SourceMessagesProcessed, on_messages)

loader = QtUiTools.QUiLoader()

# Load main window
file = QtCore.QFile(":/main.ui")
file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
# noinspection PyTypeChecker
window: QtWidgets.QMainWindow = loader.load(file, None)
file.close()

# Load main window
file = QtCore.QFile(":/about.ui")
file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
# noinspection PyTypeChecker
about_window: QtWidgets.QMainWindow = loader.load(file, None)
file.close()

# Context menus
# noinspection PyTypeChecker
menu_file: QtWidgets.QMenu = window.findChild(QtWidgets.QMenu, "menuFile")
# noinspection PyTypeChecker
menu_backlog: QtWidgets.QMenu = window.findChild(QtWidgets.QMenu, "menuBacklog")
# noinspection PyTypeChecker
menu_workitem: QtWidgets.QMenu = window.findChild(QtWidgets.QMenu, "menuEdit")
# noinspection PyTypeChecker
menu_filter: QtWidgets.QMenu = window.findChild(QtWidgets.QMenu, "menuFilter")

# Backlogs table
# noinspection PyTypeChecker
backlogs_table: QtWidgets.QTableView = window.findChild(QtWidgets.QTableView, "backlogs_table")
backlogs_table.setContextMenuPolicy(QtGui.Qt.ContextMenuPolicy.CustomContextMenu)
backlogs_table.customContextMenuRequested.connect(lambda p: menu_backlog.exec(backlogs_table.mapToGlobal(p)))
backlog_model = BacklogModel(app, source)
backlogs_table.setModel(backlog_model)
backlogs_table.selectionModel().selectionChanged.connect(backlog_changed)

# Users table
# noinspection PyTypeChecker
users_table: QtWidgets.QTableView = window.findChild(QtWidgets.QTableView, "users_table")
user_model = UserModel(app, source)
users_table.setModel(user_model)
users_table.setVisible(False)

# Workitems table
# noinspection PyTypeChecker
workitems_table: QtWidgets.QTableView = window.findChild(QtWidgets.QTableView, "workitems_table")
workitems_table.setContextMenuPolicy(QtGui.Qt.ContextMenuPolicy.CustomContextMenu)
workitems_table.customContextMenuRequested.connect(lambda p: menu_workitem.exec(workitems_table.mapToGlobal(p)))
workitems_table.setItemDelegateForColumn(2, PomodoroDelegate())
workitem_model = WorkitemModel(workitems_table, source)
workitems_table.setModel(workitem_model)
workitems_table.selectionModel().selectionChanged.connect(workitem_changed)

# Drag-and-drop doesn't work for some reason
# workitems_table.setDragEnabled(True)
# workitems_table.setAcceptDrops(True)
# workitems_table.setDropIndicatorShown(True)
# workitems_table.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
# workitems_table.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
# workitems_table.setDragDropOverwriteMode(False)

# Progress bar
# noinspection PyTypeChecker
backlog_progress: QtWidgets.QProgressBar = window.findChild(QtWidgets.QProgressBar, "footerProgress")
backlog_progress.hide()
# noinspection PyTypeChecker
backlog_progress_txt: QtWidgets.QLabel = window.findChild(QtWidgets.QLabel, "footerLabel")
backlog_progress_txt.hide()
# noinspection PyTypeChecker
search_bar: QtWidgets.QHBoxLayout = window.findChild(QtWidgets.QHBoxLayout, "searchBar")
search = SearchBar(window, source, backlogs_table, workitems_table)
search_bar.addWidget(search)

# TODO: Subscribe update_progress(backlog) to events.AfterWorkitem* and +/- pomodoro
# Can't do it now, because all those events supply workitem, but not a backlog
# Have to wait till we have a better data model

# Layouts
# noinspection PyTypeChecker
main_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "mainLayout")
# noinspection PyTypeChecker
header_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "headerLayout")
# noinspection PyTypeChecker
left_table_layout: QtWidgets.QWidget = window.findChild(QtWidgets.QWidget, "leftTableLayout")

eye_candy()

# Settings
# noinspection PyTypeChecker
settings_action: QtGui.QAction = window.findChild(QtGui.QAction, "actionSettings")
settings_action.triggered.connect(lambda: SettingsDialog(settings).show())

# Connect menu actions to the toolbar
# noinspection PyTypeChecker
quit_action: QtGui.QAction = window.findChild(QtGui.QAction, "actionQuit")
quit_action.triggered.connect(app.quit)

# noinspection PyTypeChecker
import_action: QtGui.QAction = window.findChild(QtGui.QAction, "actionImport")
import_action.triggered.connect(import_)

# noinspection PyTypeChecker
export_action: QtGui.QAction = window.findChild(QtGui.QAction, "actionExport")
export_action.triggered.connect(export)

# noinspection PyTypeChecker
action_show_main_window: QtGui.QAction = window.findChild(QtGui.QAction, "actionShowMainWindow")
action_show_main_window.triggered.connect(lambda: window.show())

# noinspection PyTypeChecker
action_backlogs: QtGui.QAction = window.findChild(QtGui.QAction, "actionBacklogs")
action_backlogs.toggled.connect(toggle_backlogs)

# noinspection PyTypeChecker
action_teams: QtGui.QAction = window.findChild(QtGui.QAction, "actionTeams")
action_teams.toggled.connect(toggle_users)

# noinspection PyTypeChecker
action_show_completed_workitems: QtGui.QAction = window.findChild(QtGui.QAction, "actionShowCompletedWorkitems")
action_show_completed_workitems.toggled.connect(toggle_show_completed_workitems)

# noinspection PyTypeChecker
action_new_backlog: QtGui.QAction = window.findChild(QtGui.QAction, "actionNewBacklog")
action_new_backlog.triggered.connect(create_backlog)

# noinspection PyTypeChecker
action_delete_backlog: QtGui.QAction = window.findChild(QtGui.QAction, "actionDeleteBacklog")
action_delete_backlog.triggered.connect(delete_backlog)

# noinspection PyTypeChecker
action_rename_backlog: QtGui.QAction = window.findChild(QtGui.QAction, "actionRenameBacklog")
action_rename_backlog.triggered.connect(rename_backlog)

# noinspection PyTypeChecker
action_new_workitem: QtGui.QAction = window.findChild(QtGui.QAction, "actionNewWorkitem")
action_new_workitem.triggered.connect(create_workitem)

# noinspection PyTypeChecker
action_delete_workitem: QtGui.QAction = window.findChild(QtGui.QAction, "actionDeleteWorkitem")
action_delete_workitem.triggered.connect(delete_workitem)

# noinspection PyTypeChecker
action_rename_workitem: QtGui.QAction = window.findChild(QtGui.QAction, "actionRenameWorkitem")
action_rename_workitem.triggered.connect(rename_workitem)

# noinspection PyTypeChecker
action_complete_workitem: QtGui.QAction = window.findChild(QtGui.QAction, "actionCompleteWorkitem")
action_complete_workitem.triggered.connect(complete_work)

# noinspection PyTypeChecker
action_start: QtGui.QAction = window.findChild(QtGui.QAction, "actionStart")
action_start.triggered.connect(start_work)

# noinspection PyTypeChecker
action_add_pomodoro: QtGui.QAction = window.findChild(QtGui.QAction, "actionAddPomodoro")
action_add_pomodoro.triggered.connect(add_pomodoro)

# noinspection PyTypeChecker
action_remove_pomodoro: QtGui.QAction = window.findChild(QtGui.QAction, "actionRemovePomodoro")
action_remove_pomodoro.triggered.connect(remove_pomodoro)

# noinspection PyTypeChecker
action_search: QtGui.QAction = window.findChild(QtGui.QAction, "actionSearch")
action_search.triggered.connect(lambda: search.show())

# noinspection PyTypeChecker
action_void: QtGui.QAction = window.findChild(QtGui.QAction, "actionVoid")
action_void.triggered.connect(lambda: void_pomodoro())

# noinspection PyTypeChecker
action_about: QtGui.QAction = window.findChild(QtGui.QAction, "actionAbout")
action_about.triggered.connect(lambda: show_about())

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
tray = QtWidgets.QSystemTrayIcon()
tray.activated.connect(lambda reason: (tray_clicked() if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger else None))
menu = QtWidgets.QMenu()
menu.addAction(action_void)
menu.addSeparator()
menu.addAction(action_show_main_window)
menu.addAction(settings_action)
menu.addAction(quit_action)
tray.setContextMenu(menu)
reset_tray_icon()
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

# noinspection PyTypeChecker
tool_settings: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolSettings")
tool_settings.clicked.connect(lambda: menu_file.exec(
    tool_settings.parentWidget().mapToGlobal(tool_settings.geometry().center())
))

# Splitter
# noinspection PyTypeChecker
splitter: QtWidgets.QSplitter = window.findChild(QtWidgets.QSplitter, "splitter")
splitter.splitterMoved.connect(save_splitter_size)

# Header
# noinspection PyTypeChecker
tool_void: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolVoid")
tool_void.setDefaultAction(action_void)
tool_void.hide()

# noinspection PyTypeChecker
tool_next: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolNext")
tool_next.clicked.connect(lambda: start_work())     # TODO Start next, not current
tool_next.hide()

# noinspection PyTypeChecker
tool_complete: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolComplete")
tool_complete.clicked.connect(lambda: complete_work())  # TODO Complete next, not current
tool_complete.hide()

# noinspection PyTypeChecker
tool_note: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolNote")
tool_note.clicked.connect(lambda: note_pomodoro())

# noinspection PyTypeChecker
tool_filter: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolFilter")
tool_filter.clicked.connect(lambda: menu_filter.exec(
    tool_filter.parentWidget().mapToGlobal(tool_filter.geometry().center())
))

# noinspection PyTypeChecker
tool_show_all: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolShowAll")
tool_show_all.clicked.connect(hide_timer)
tool_show_all.hide()

# noinspection PyTypeChecker
tool_show_timer_only: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "toolShowTimerOnly")
tool_show_timer_only.clicked.connect(show_timer)

# noinspection PyTypeChecker
header_text: QtWidgets.QLabel = window.findChild(QtWidgets.QLabel, "headerText")
# noinspection PyTypeChecker
header_subtext: QtWidgets.QLabel = window.findChild(QtWidgets.QLabel, "headerSubtext")

# Fonts, styles, etc.
initialize_fonts(settings)

auto_resize()  # It's important to do it after the fonts are set
restore_size()
event_filter = MainWindowEventFilter(window)
window.installEventFilter(event_filter)
window.move(app.primaryScreen().geometry().center() - window.frameGeometry().center())

window.show()

source.start()

sys.exit(app.exec())

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
from typing import Callable

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget, QAbstractItemView, QToolButton

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged, BeforeSourceChanged
from fk.core.events import AfterSettingsChanged, SourceMessagesProcessed, AfterBacklogCreate, \
    AfterBacklogRename, AfterWorkitemCreate, AfterWorkitemRename, AfterPomodoroAdd, AfterPomodoroRemove, \
    AfterPomodoroWorkStart, AfterPomodoroComplete, AfterWorkitemComplete
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.configurable_toolbar import ConfigurableToolBar
from fk.qt.info_overlay import show_tutorial_overlay
from fk.qt.qt_timer import QtTimer
from fk.qt.workitem_tableview import WorkitemTableView

logger = logging.getLogger(__name__)


def _get_row_position(widget: QAbstractItemView, x: float, row: int, col: int, arrow: str) -> QPoint:
    row_rect = widget.visualRect(widget.model().index(row, col))
    return widget.mapToGlobal(QPoint(
        round(row_rect.left() * (1.0 - x) + x * row_rect.right()),
        row_rect.top() + 5 if arrow == 'down' else row_rect.bottom() + 5
    ))


class Tutorial:
    _source_holder: EventSourceHolder
    _settings: AbstractSettings
    _main_window: QWidget

    _steps: dict[str, Callable]

    def __init__(self,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings,
                 main_window: QWidget):
        super().__init__()
        self._settings = settings
        self._source_holder = source_holder
        self._main_window = main_window
        self._steps = {
            SourceMessagesProcessed: self._on_messages,
            AfterBacklogCreate: self._on_backlog_create,
            AfterBacklogRename: self._on_backlog_rename,
            AfterWorkitemCreate: self._on_workitem_create,
            AfterWorkitemRename: self._on_workitem_rename,
            AfterPomodoroAdd: self._on_pomodoro_add,
            AfterPomodoroRemove: self._on_pomodoro_remove,
            AfterPomodoroWorkStart: self._on_pomodoro_work_start,
            AfterPomodoroComplete: self._on_pomodoro_complete,
            AfterWorkitemComplete: self._on_workitem_complete,
        }

        settings.on(AfterSettingsChanged, self._on_setting_changed)
        if settings.get('Application.show_tutorial') == 'True':
            self._subscribe()

    def _subscribe(self):
        logger.debug(f'Subscribing tutorial to source_holder changes')
        self._source_holder.on(BeforeSourceChanged, self._before_source_changed, True)
        self._source_holder.on(AfterSourceChanged, self._after_source_changed, True)

    def _unsubscribe(self):
        logger.debug(f'Unsubscribing the tutorial')
        self._source_holder.unsubscribe(self._after_source_changed)
        self._source_holder.unsubscribe(self._before_source_changed)
        source = self._source_holder.get_source()
        if source is not None:
            source.unsubscribe(self._on_event)

    def _on_event(self, event: str, **kwargs):
        if self._is_to_complete(event):
            self._steps[event](lambda: self._mark_completed(event),
                               lambda: self._settings.set({'Application.show_tutorial': 'False'}),
                               **kwargs)

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        if 'Application.show_tutorial' in new_values:
            show = new_values['Application.show_tutorial'] == 'True'
            self._subscribe() if show else self._unsubscribe()

    def _mark_completed(self, step: str) -> None:
        setting = self._settings.get('Application.completed_tutorial_steps')
        steps: list[str] = [] if setting == '' else setting.split(',')
        if step not in steps:
            steps.append(step)
        self._settings.set({'Application.completed_tutorial_steps': ','.join(steps)})
        # Disable tutorial if we completed everything
        logger.debug(f'Marking tutorial step {step} complete. All completed steps: {steps}')
        if len(steps) == len(self._steps):
            logger.debug(f'Disabling the tutorial')
            self._settings.set({'Application.show_tutorial': 'False'})

    def _is_to_complete(self, step: str) -> bool:
        return step not in self._settings.get('Application.completed_tutorial_steps').split(',')

    def _before_source_changed(self, event: str, source: AbstractEventSource) -> None:
        # Here we are dealing with the OLD source, from which we want to unsubscribe
        if source is not None:
            logger.debug(f'Unsubscribing tutorial from old source events')
            for event in self._steps:
                source.on(event, self._on_event)

    def _after_source_changed(self, event: str, source: AbstractEventSource) -> None:
        logger.debug(f'Subscribing tutorial to new source events')
        for event in self._steps:
            source.on(event, self._on_event)

    def _get_toolbar_button_position(self, action_name: str, arrow: str):
        toolbar: ConfigurableToolBar
        if action_name.startswith('backlogs_table'):
            toolbar = self._main_window.findChild(ConfigurableToolBar, "backlogs_toolbar")
        else:
            toolbar = self._main_window.findChild(ConfigurableToolBar, "workitems_toolbar")
        rect = toolbar.get_button_geometry(action_name)
        pt = rect.center()
        pt.setY(rect.top() if arrow == 'down' else rect.bottom())
        return toolbar.parentWidget().mapToGlobal(pt)

    # Tutorial "steps" implementation are only called if the corresponding step hasn't been completed yet.
    # The "complete" parameter is a callback, which the step can execute to mark it completed.

    def _on_messages(self, complete: Callable, skip: Callable, **kwargs) -> None:
        show_tutorial_overlay('1 / 11: Welcome to Flowkeeper! Let\'s start by creating your first backlog. You would '
                              'usually create a new one every morning.\n\n'
                              'Hotkey: Ctrl+N / ⌘N',
                              self._get_toolbar_button_position('backlogs_table.newBacklog', 'up'),
                              'info',
                              complete,
                              skip,
                              'up')

    def _on_backlog_create(self, complete: Callable, skip: Callable, **kwargs) -> None:
        backlogs: BacklogTableView = self._main_window.findChild(BacklogTableView, "backlogs_table")
        show_tutorial_overlay('2 / 11: Type some catchy name for your backlog and press Enter.\n\n'
                              'You can rename existing backlogs by double-clicking them or pressing Ctrl+R / ⌘R.',
                              _get_row_position(backlogs, 0.15, 0, 0, 'down'),
                              'info',
                              complete,
                              skip,
                              'down')

    def _on_backlog_rename(self, complete: Callable, skip: Callable, **kwargs) -> None:
        show_tutorial_overlay('3 / 11: Now create a work item in the selected backlog. Work items are tasks, '
                              'which you can execute using Pomodoro Technique.\n\n'
                              'Hotkey: Ins',
                              self._get_toolbar_button_position('workitems_table.newItem', 'up'),
                              'info',
                              complete,
                              skip,
                              'up')

    def _on_workitem_create(self, complete: Callable, skip: Callable, **kwargs) -> None:
        workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
        show_tutorial_overlay('4 / 11: Choose a better name for this work item and press Enter.\n\n'
                              'Just like backlogs, you can rename work items by double-clicking them or '
                              'by pressing F6.',
                              _get_row_position(workitems, 0.15, 0, 1, 'down'),
                              'info',
                              complete,
                              skip,
                              'down')

    def _on_workitem_rename(self, complete: Callable, skip: Callable, workitem: Workitem, **kwargs) -> None:
        show_tutorial_overlay('5 / 11: Before you can start working on it, you need to estimate this task in '
                              '25-minute pomodoros. Add several pomodoros by clicking this button.\n\n'
                              'Hotkey: Ctrl++ / ⌘+',
                              self._get_toolbar_button_position('workitems_table.addPomodoro', 'down'),
                              'info',
                              complete,
                              skip,
                              'down')

    def _on_pomodoro_add(self, complete: Callable, skip: Callable, workitem: Workitem, **kwargs) -> None:
        if len(workitem) >= 3:
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay('6 / 11: If you overestimated your work item, you can delete excessive pomodoros. '
                                  'Leave at least two pomodoros to continue the tutorial.\n\n'
                                  'Hotkey: Ctrl+- / ⌘-',
                                  _get_row_position(workitems, 0.5, 0, 2, 'up'),
                                  'info',
                                  complete,
                                  skip,
                                  'up')

    def _on_pomodoro_remove(self, complete: Callable, skip: Callable, workitem: Workitem, **kwargs) -> None:
        if len(workitem) >= 2:
            show_tutorial_overlay(f'7 / 11: Now you are ready to start your first pomodoro by clicking ▶️ button '
                                  f'in the toolbar.\n\n'
                                  f'Hotkey: Ctrl+S / ⌘S',
                                  self._get_toolbar_button_position('workitems_table.startItem', 'down'),
                                  'info',
                                  complete,
                                  skip,
                                  'down')

    def _on_pomodoro_work_start(self, complete: Callable, skip: Callable, **kwargs) -> None:
        def do(_):
            timer: QToolButton = self._main_window.findChild(QToolButton, "focus.voidPomodoro")
            pt: QPoint = timer.rect().center()
            pt.setY(timer.rect().bottom() + 15)
            show_tutorial_overlay(f'8 / 11: Take a minute to explore this view. We call it Focus Mode, and this is '
                                  f'where Flowkeeper spends most of its time. You can customize this view in the '
                                  f'Settings.\n\n'
                                  f'You probably don\'t want to wait for 25 minutes to continue this tutorial, so '
                                  f'please void this pomodoro by clicking X button in the middle of the timer '
                                  f'indicator.',
                                  timer.mapToGlobal(pt),
                                  'info',
                                  complete,
                                  skip,
                                  'up')
        # We decouple it through a timer to make sure all resizing is done by the time we display the overlay
        QtTimer('tutorial-on_pomodoro_work_start').schedule(100, do, None, True)

    def _on_pomodoro_complete(self, complete: Callable, skip: Callable, pomodoro: Pomodoro, **kwargs) -> None:
        completed_count = 0
        for p in self._source_holder.get_source().pomodoros():
            if p.is_finished() or p.is_canceled():
                completed_count += 1
        if completed_count == 1:
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay(f'9 / 11: {"We are very sorry that you had to void" if pomodoro.is_canceled() else "Congratulations! You successfully completed"} your first pomodoro. '
                                  'Note how its icon changed.\n\n'
                                  'You might have heard a DING when that happened -- you can configure all Flowkeeper '
                                  'sounds in the Settings > Audio.\n\n'
                                  'Now try to complete another pomodoro, this time see what different buttons in that '
                                  'Focus Mode do. Also pay attention to the Flowkeeper icon in system tray.',
                                  _get_row_position(workitems, 0.4, 0, 2, 'up'),
                                  'info',
                                  lambda: None,
                                  skip,
                                  'up')
        elif completed_count > 1:
            show_tutorial_overlay('10 / 11: Well done! Now let\'s imagine that you finished this work item. You can '
                                  'mark it completed by clicking the ✔️ button.\n\n'
                                  f'Hotkey: Ctrl+P / ⌘P',
                                  self._get_toolbar_button_position('workitems_table.completeItem', 'down'),
                                  'info',
                                  complete,
                                  skip,
                                  'down')

    def _on_workitem_complete(self, complete: Callable, skip: Callable, **kwargs) -> None:
        workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
        show_tutorial_overlay('11 / 11: Note that as you marked that work item completed you can\'t modify it anymore. '
                              'The only thing you can do is delete it.\n\n'
                              'Hotkey: Del\n\n'
                              'Great job, you finished this tutorial!',
                              _get_row_position(workitems, 0.15, 0, 1, 'up'),
                              'info',
                              complete,
                              skip,
                              'up')

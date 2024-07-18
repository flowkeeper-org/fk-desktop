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
from PySide6.QtWidgets import QWidget, QAbstractItemView

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import AfterSettingsChanged, SourceMessagesProcessed, AfterBacklogCreate, \
    AfterBacklogRename, AfterWorkitemCreate, AfterWorkitemRename, AfterPomodoroAdd, AfterPomodoroRemove, \
    AfterPomodoroWorkStart, AfterPomodoroComplete, AfterWorkitemComplete
from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.focus_widget import FocusWidget
from fk.qt.info_overlay import show_tutorial_overlay
from fk.qt.workitem_tableview import WorkitemTableView

logger = logging.getLogger(__name__)


def _get_row_position(widget: QAbstractItemView, row: int, col: int = 0) -> QPoint:
    row_rect = widget.visualRect(widget.model().index(row, col))
    return QPoint(row_rect.center().x() * 0.5, row_rect.bottomRight().y() + 10)


def get_tutorial_step(step: int, main_window: QWidget) -> (str, QPoint, str):
    logger.debug(f'Tutorial step {step}')
    if step == 1:
        backlogs: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        return '1 / 10: Backlogs are To Do lists. You would usually start your day by creating a new backlog.', \
            backlogs.parentWidget().mapToGlobal(backlogs.rect().center()), 'info'
    elif step == 2:
        backlogs: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")

        pos = _get_row_position(backlogs, 1)
        # return '1 / 10: Backlogs are To Do lists. You would usually start your day by creating a new backlog. ' \
        #        'You can create project backlogs, long-term to-do lists, etc.', \
        #     backlogs.mapToGlobal(pos)
        return '1 / 10: Backlogs are To Do lists.', backlogs.parentWidget().mapToGlobal(pos), 'arrow'
        # backlogs.parentWidget().mapToGlobal(backlogs.rect().center())
    elif step == 3:
        workitems: WorkitemTableView = main_window.findChild(WorkitemTableView, "workitems_table")
        return '2 / 10: Work items', workitems.parentWidget().mapToGlobal(workitems.rect().center()), 'info'
    elif step == 4:
        return '3 / 10: Thank you!', main_window.mapToGlobal(main_window.rect().center()), 'info'


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
        print(f'Subscribing tutorial to source_holder changes')
        self._source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _unsubscribe(self):
        print(f'Unsubscribing the tutorial')
        self._source_holder.unsubscribe(self._on_source_changed)
        source = self._source_holder.get_source()
        if source is not None:
            source.unsubscribe(self._on_event)

    def _on_event(self, event: str, **kwargs):
        if self._is_to_complete(event):
            self._steps[event](lambda: self._mark_completed(event), **kwargs)

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
        print(f'Marking tutorial step {step} complete. All completed steps: {steps}')
        if len(steps) == len(self._steps):
            print(f'Disabling the tutorial')
            self._settings.set({'Application.show_tutorial': 'False'})

    def _is_to_complete(self, step: str) -> bool:
        return step not in self._settings.get('Application.completed_tutorial_steps').split(',')

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        print(f'Subscribing tutorial to source events')
        for event in self._steps:
            source.on(event, self._on_event)

    # Tutorial "steps" implementation are only called if the corresponding step hasn't been completed yet.
    # The "complete" parameter is a callback, which the step can execute to mark it completed.

    def _on_messages(self, complete: Callable, **kwargs) -> None:
        if next(iter(self._source_holder.get_source().backlogs()), None) is None:   # I.e. there are no backlogs
            backlogs: BacklogTableView = self._main_window.findChild(BacklogTableView, "backlogs_table")
            show_tutorial_overlay('Welcome to Flowkeeper! Start by creating your first backlog.',
                                  backlogs.parentWidget().mapToGlobal(backlogs.rect().center()),
                                  'info',
                                  complete)
        else:
            complete()

    def _on_backlog_create(self, complete: Callable, **kwargs) -> None:
        backlogs: BacklogTableView = self._main_window.findChild(BacklogTableView, "backlogs_table")
        show_tutorial_overlay('Pick a new name for your backlog and press Enter. You can rename existing backlogs '
                              'by double-clicking or pressing F2.',
                              backlogs.parentWidget().mapToGlobal(backlogs.rect().center()),
                              'info',
                              complete)

    def _on_backlog_rename(self, complete: Callable, **kwargs) -> None:
        if next(iter(self._source_holder.get_source().workitems()), None) is None:   # I.e. there are no workitems
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay('Create a work item in the selected backlog.',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  complete)
        else:
            complete()

    def _on_workitem_create(self, complete: Callable, **kwargs) -> None:
        show_tutorial_overlay('Pick a better name for this workitem and press Enter.',
                              self._main_window.mapToGlobal(self._main_window.rect().center()),
                              'info',
                              complete)

    def _on_workitem_rename(self, complete: Callable, workitem: Workitem, **kwargs) -> None:
        if len(workitem) == 0:   # I.e. there are no pomodoros
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay('Add several pomodoros by pressing Ctrl-[+] on the selected workitem a few times',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  complete)
        else:
            complete()

    def _on_pomodoro_add(self, complete: Callable, workitem: Workitem, **kwargs) -> None:
        if len(workitem) >= 3:
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay('Try to delete one by pressing Ctrl-[-]. Leave at least two pomodoros to continue.',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  complete)

    def _on_pomodoro_remove(self, complete: Callable, workitem: Workitem, **kwargs) -> None:
        if len(workitem) >= 2:
            workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
            show_tutorial_overlay(f'Now you are ready to start working on work item "{workitem.get_name()}". To '
                                  f'do that press Ctrl+S (Start) or click ▶️ button in the toolbar.',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  complete)

    def _on_pomodoro_work_start(self, complete: Callable, **kwargs) -> None:
        focus: FocusWidget = self._main_window.findChild(FocusWidget, "focus")
        show_tutorial_overlay(f'The timer will tick for 25 minutes, which is a default Pomodoro duration. '
                              f'Void it.',
                              focus.parentWidget().mapToGlobal(focus.rect().center()),
                              'info',
                              complete)

    def _on_pomodoro_complete(self, complete: Callable, pomodoro: Pomodoro, **kwargs) -> None:
        workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
        completed_count = 0
        for p in self._source_holder.get_source().pomodoros():
            if p.is_finished() or p.is_canceled():
                completed_count += 1
        if completed_count == 1:
            show_tutorial_overlay(f'{"You voided" if pomodoro.is_canceled() else "Congratulations! You successfully completed"} a pomodoro. '
                                  'Note how its icon changed. Try to complete another pomodoro, this time see what you can '
                                  'do with that Focus window. Also pay attention to the Flowkeeper icon in system tray.',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  lambda: None)
        elif completed_count > 1:
            show_tutorial_overlay('Now let\'s say you are done with this work item. You can mark it completed by '
                                  'pressing Ctrl+P, or via ✔️ icon.',
                                  workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                                  'info',
                                  complete)

    def _on_workitem_complete(self, complete: Callable, **kwargs) -> None:
        workitems: WorkitemTableView = self._main_window.findChild(WorkitemTableView, "workitems_table")
        show_tutorial_overlay('Now as you marked work item completed you can\'t modify it anymore. The only thing you '
                              'can do is delete it. This concludes the tutorial.',
                              workitems.parentWidget().mapToGlobal(workitems.rect().center()),
                              'info',
                              complete)

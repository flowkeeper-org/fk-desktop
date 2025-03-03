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
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.pomodoro import POMODORO_TYPE_NORMAL
from fk.core.tag import Tag
from fk.core.timer_data import TimerData


class ProgressWidget(QWidget):
    _label: QLabel

    def __init__(self,
                 parent: QWidget,
                 source_holder: EventSourceHolder):
        super().__init__(parent)
        self.setObjectName('progress')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._label = QLabel(self)
        self._label.setObjectName("footerLabel")
        layout.addWidget(self._label)
        self.setVisible(False)
        source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _on_source_changed(self, event: str, source: AbstractEventSource) -> None:
        self.update_progress(None)
        source.on("AfterWorkitem*", lambda workitem, **kwargs: self.update_progress(workitem.get_parent()))
        source.on('AfterPomodoro*',
                  lambda **kwargs: self.update_progress(
                      kwargs['workitem'].get_parent() if 'workitem' in kwargs else kwargs['pomodoro'].get_parent().get_parent()
                  ))

    def update_progress(self, backlog_or_tag: Backlog | Tag | None) -> None:
        total: int = 0
        done: int = 0
        in_series: int = -1
        if backlog_or_tag:
            workitems = backlog_or_tag.values() if type(backlog_or_tag) is Backlog else backlog_or_tag.get_workitems()
            timer: TimerData = backlog_or_tag.get_parent().get_timer() if type(backlog_or_tag) is Backlog else backlog_or_tag.get_parent().get_parent().get_timer()
            in_series = timer.get_pomodoro_in_series()
            for wi in workitems:
                for p in wi.values():
                    if p.get_type() == POMODORO_TYPE_NORMAL:
                        total += 1
                        if p.is_finished():
                            done += 1

        self.setVisible(total > 0)
        self._label.setVisible(total > 0)
        percent = f' ({round(100 * done / total)}%)' if total > 0 else ''
        series = f', {in_series} in this series' if in_series > 0 else ''
        self._label.setText(f'Done {done} of {total} pomodoros{percent}{series}')

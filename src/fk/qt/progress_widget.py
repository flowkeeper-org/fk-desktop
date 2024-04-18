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

from fk.core.backlog import Backlog
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged


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

    def _on_source_changed(self, event, source):
        source.on("AfterWorkitem*", lambda workitem, **kwargs: self.update_progress(workitem.get_parent()))
        source.on("AfterPomodoro*", lambda workitem, **kwargs: self.update_progress(workitem.get_parent()))

    def update_progress(self, backlog: Backlog) -> None:
        total: int = 0
        done: int = 0
        for wi in backlog.values():
            for p in wi.values():
                total += 1
                if p.is_finished() or p.is_canceled():
                    done += 1

        self.setVisible(total > 0)
        self._label.setVisible(total > 0)
        percent = f' ({round(100 * done / total)}%)' if total > 0 else ''
        self._label.setText(f'{done} of {total} done{percent}')

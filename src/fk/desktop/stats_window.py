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

from PySide6.QtCharts import QChart, QBarSet, QBarCategoryAxis, QValueAxis, QChartView, QStackedBarSeries
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QApplication

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.file_event_source import FileEventSource
from fk.core.no_cryptograph import NoCryptograph
from fk.core.tenant import Tenant
from fk.qt.qt_settings import QtSettings


class StatsWindow(QMainWindow):
    _chart: QChart
    _source: AbstractEventSource

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent)
        self._source = source
        self.setWindowTitle('Pomodoro Statistics')
        self.resize(700, 500)
        chart = QChart()
        self._chart = chart
        bar_finished = QBarSet("Completed", self)
        bar_canceled = QBarSet("Voided", self)
        bar_startable = QBarSet("Not started", self)
        axis_x = QBarCategoryAxis(self)
        axis_y = QValueAxis(self)
        axis_y.setLabelFormat('%d')
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series = QStackedBarSeries(self)    # or QBarSeries
        chart.addSeries(series)
        series.append(bar_finished)
        series.append(bar_canceled)
        series.append(bar_startable)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        d = self.extract_data('month')
        axis_y.setRange(0, max(d[4]))
        axis_x.append(d[0])
        [bar_finished.append(i) for i in d[1]]
        [bar_canceled.append(i) for i in d[2]]
        [bar_startable.append(i) for i in d[3]]

        view = QChartView(chart, self)
        self.setCentralWidget(view)

    def extract_data(self, group: str):
        if group == 'weekday':
            cats = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        elif group == 'month':
            cats = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        else:
            raise Exception(f'Grouping by {group} is not implemented')

        list_finished = [0 for c in cats]
        list_canceled = [0 for c in cats]
        list_ready = [0 for c in cats]
        list_total = [0 for c in cats]

        for p in self._source.pomodoros():
            finished = p.is_finished()
            canceled = p.is_canceled()
            if finished or canceled:
                when = p.get_last_modified_date()
            else:
                when = p.get_create_date()
            if when is None:
                continue

            index = 0
            if group == 'weekday':
                index = when.weekday()
            elif group == 'month':
                index = when.month - 1

            if finished:
                list_finished[index] += 1
            elif canceled:
                list_canceled[index] += 1
            else:
                list_ready[index] += 1
            list_total[index] += 1

        return cats, list_finished, list_canceled, list_ready, list_total


if __name__ == '__main__':
    app = QApplication([])
    settings = QtSettings()
    src = FileEventSource[Tenant](settings, NoCryptograph(settings), Tenant(settings))
    src.start()
    stats = StatsWindow(None, src)
    stats.show()
    sys.exit(app.exec())

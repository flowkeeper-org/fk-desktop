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
from calendar import monthrange
from typing import Callable

from PySide6 import QtUiTools
from PySide6.QtCharts import QChart, QBarSet, QBarCategoryAxis, QValueAxis, QChartView, QStackedBarSeries
from PySide6.QtCore import Qt, QObject, QFile, QMargins
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QWidget, QApplication, QVBoxLayout, QLabel, QToolButton

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.file_event_source import FileEventSource
from fk.core.no_cryptograph import NoCryptograph
from fk.core.tenant import Tenant
from fk.qt.qt_settings import QtSettings


class StatsWindow(QObject):
    _chart: QChart
    _source: AbstractEventSource
    _stats_window: QMainWindow
    _header_text: QLabel
    _header_subtext: QLabel
    _period_actions: dict[str, QAction]
    _prev_action: QAction
    _next_action: QAction

    _to: datetime.datetime
    _period: str

    _series: QStackedBarSeries
    _axis_x: QBarCategoryAxis
    _axis_y: QValueAxis
    _bars: dict[str, QBarSet]

    def __init__(self, parent: QWidget, application: QApplication, source: AbstractEventSource):
        super().__init__(parent)
        self._source = source
        self._period = 'week'
        self._to = self._drop_time(datetime.datetime.now(datetime.timezone.utc), self._period)

        file = QFile(":/stats.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._stats_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

        self._header_text = self._stats_window.findChild(QLabel, "statsHeaderText")
        self._header_text.setFont(application.get_header_font())

        self._header_subtext = self._stats_window.findChild(QLabel, "statsHeaderSubtext")
        self._period_actions = {
            'year': self._create_checkable_action('year'),
            'month6': self._create_checkable_action('month6'),
            'month': self._create_checkable_action('month'),
            'week': self._create_checkable_action('week'),
            'day': self._create_checkable_action('day'),
        }
        self._period_actions['week'].setChecked(True)
        self._prev_action = self._create_simple_action('prev', self._prev)
        self._next_action = self._create_simple_action('next', self._next)

        self._stats_window.setWindowTitle('Pomodoro Statistics')
        self._stats_window.resize(700, 500)
        chart = QChart()
        self._chart = chart
        axis_x = QBarCategoryAxis(self)
        self._axis_x = axis_x
        axis_y = QValueAxis(self)
        self._axis_y = axis_y
        axis_y.setLabelFormat('%d')
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        self._series = QStackedBarSeries(self)    # or QBarSeries
        chart.addSeries(self._series)
        self._series.attachAxis(self._axis_x)
        self._series.attachAxis(self._axis_y)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setMargins(QMargins(10, 0, 10, 0))
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        self._update_chart('week', self._to)

        layout: QVBoxLayout = self._stats_window.findChild(QVBoxLayout, "statsGraph")
        view = QChartView(chart, self._stats_window)
        view.setObjectName('statsView')
        chart.setTheme(QChart.ChartTheme.ChartThemeDark if application.is_dark_theme() else QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)
        layout.addWidget(view)

    def _time_delta_for_period(self, period: str, date: datetime.datetime, left: bool):
        date = self._drop_time(date, period)
        if period == 'week':
            return datetime.timedelta(days=(-7 if left else 7))
        elif period == 'year':
            year = date.year + (-1 if left else 1)
            cmp_date = datetime.datetime(year,
                                         date.month,
                                         min(date.day, monthrange(year, date.month)[1]),
                                         date.hour,
                                         tzinfo=date.tzinfo)
            return cmp_date - date
        elif period == 'day':
            return datetime.timedelta(days=(-1 if left else 1))
        elif period == 'month':
            year = date.year
            month = date.month
            if left:
                if month == 1:
                    month = 12
                    year -= 1
                else:
                    month -= 1
            else:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1
            cmp_date = datetime.datetime(year,
                                         month,
                                         min(date.day, monthrange(year, month)[1]),
                                         date.hour,
                                         tzinfo=date.tzinfo)
            return cmp_date - date
        elif period == 'month6':
            delta = datetime.timedelta()
            for i in range(6):
                delta += self._time_delta_for_period('month', date + delta, left)
            return delta
        else:
            raise Exception(f'Unexpected period: {period}')

    def _drop_time(self, date: datetime.datetime, period: str):
        if period == 'week':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     tzinfo=date.tzinfo)
        elif period == 'year':
            return datetime.datetime(date.year,
                                     date.month,
                                     monthrange(date.year, date.month)[1],
                                     tzinfo=date.tzinfo)
        elif period == 'day':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     date.hour,
                                     tzinfo=date.tzinfo)
        elif period == 'month':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     tzinfo=date.tzinfo)
        elif period == 'month6':
            return datetime.datetime(date.year,
                                     date.month,
                                     monthrange(date.year, date.month)[1],
                                     tzinfo=date.tzinfo)
        else:
            raise Exception(f'Unexpected period: {period}')

    def _substep_delta_for_period(self, period: str, date: datetime.datetime, left: bool):
        if period == 'week':
            return self._time_delta_for_period('day', date, left)
        elif period == 'year':
            return self._time_delta_for_period('month', date, left)
        elif period == 'day':
            return datetime.timedelta(hours=(-6 if left else 6))
        elif period == 'month':
            return self._time_delta_for_period('week', date, left)
        elif period == 'month6':
            return self._time_delta_for_period('month', date, left)
        else:
            raise Exception(f'Unexpected period: {period}')

    def _prev(self):
        self._to = self._drop_time(self._to, self._period)
        self._to += self._substep_delta_for_period(self._period, self._to, True)
        self._update_chart(self._period, self._to)

    def _next(self):
        self._to = self._drop_time(self._to, self._period)
        self._to += self._substep_delta_for_period(self._period, self._to, False)
        self._update_chart(self._period, self._to)

    def _format_date(self, date: datetime.datetime):
        return date.strftime('%d %b %Y')

    def _update_chart(self, period: str, to: datetime.datetime) -> None:
        self._period = period
        _from: datetime.datetime = to + self._time_delta_for_period(period, to, True)
        self._header_subtext.setText(f'Average over {self._format_date(_from)} to {self._format_date(to)}')

        d = self.extract_data(period, _from, to)

        completed_count = sum(d[1])
        total_count = completed_count + sum(d[2]) + sum(d[3])
        percentage = f'({round(100 * completed_count / total_count)}%)' if total_count > 0 else ''
        self._header_text.setText(f'Completed {completed_count} out of {total_count} {percentage}')

        self._axis_y.setRange(0, max(d[4]))
        self._axis_x.clear()
        self._axis_x.append(d[0])

        self._bars = {
            'finished': QBarSet("Completed", self),
            'canceled': QBarSet("Voided", self),
            'startable': QBarSet("Not started", self),
        }
        self._series.clear()
        self._series.append(self._bars['finished'])
        self._series.append(self._bars['canceled'])
        self._series.append(self._bars['startable'])

        [self._bars['finished'].append(i) for i in d[1]]
        [self._bars['canceled'].append(i) for i in d[2]]
        [self._bars['startable'].append(i) for i in d[3]]

    def _create_checkable_action(self, name: str) -> QAction:
        button: QToolButton = self._stats_window.findChild(QToolButton, name)
        action = QAction(button.text(), self)
        action.setCheckable(True)
        button.setDefaultAction(action)
        action.triggered.connect(lambda: self.select_period(name))
        return action

    def _create_simple_action(self, name: str, callback: Callable) -> QAction:
        button: QToolButton = self._stats_window.findChild(QToolButton, name)
        action = QAction(button.text(), self)
        button.setDefaultAction(action)
        action.triggered.connect(callback)
        return action

    def select_period(self, period: str) -> None:
        for name in self._period_actions:
            action = self._period_actions[name]
            action.setChecked(name == period)
        self._update_chart(period, self._to)

    def _rotate(self, lst: list, n: int) -> list:
        return lst[n + 1:] + lst[:n + 1]

    def extract_data(self, group: str, period_from: datetime.datetime, period_to: datetime.datetime):
        if group == 'week':
            cats = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            rotate_around = period_to.weekday()
        elif group == 'year':
            cats = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            rotate_around = period_to.month - 1
        elif group == 'day':
            cats = [str(i) for i in range(24)]
            rotate_around = period_to.hour - 1
        elif group == 'month':
            cats = [str(i + 1) for i in range(31)]
            rotate_around = period_to.day - 1
        elif group == 'month6':
            cats = [str(i + 1) for i in range(53)]
            rotate_around = period_to.isocalendar()[1] - 1
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

            if when < period_from or when > period_to:
                continue

            index = 0
            if group == 'week':
                index = when.weekday()
            elif group == 'year':
                index = when.month - 1
            elif group == 'day':
                index = when.hour - 1
            elif group == 'month':
                index = when.day - 1
            elif group == 'month6':
                index = when.isocalendar()[1] - 1

            if finished:
                list_finished[index] += 1
            elif canceled:
                list_canceled[index] += 1
            else:
                list_ready[index] += 1
            list_total[index] += 1

        return self._rotate(cats, rotate_around), \
            self._rotate(list_finished, rotate_around), \
            self._rotate(list_canceled, rotate_around), \
            self._rotate(list_ready, rotate_around), \
            self._rotate(list_total, rotate_around)

    def show(self):
        self._stats_window.show()


if __name__ == '__main__':
    app = QApplication([])
    settings = QtSettings()
    src = FileEventSource[Tenant](settings, NoCryptograph(settings), Tenant(settings))
    src.start()
    stats = StatsWindow(None, None, src)
    stats.show()
    sys.exit(app.exec())

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
from calendar import monthrange
from typing import Callable

from PySide6 import QtUiTools
from PySide6.QtCharts import QChart, QBarSet, QBarCategoryAxis, QValueAxis, QChartView, QStackedBarSeries
from PySide6.QtCore import Qt, QObject, QFile, QMargins
from PySide6.QtGui import QAction, QPainter, QColor, QFont
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QToolButton

from fk.core.abstract_event_source import AbstractEventSource


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

    _color_highlight: QColor
    _color_primary: QColor
    _color_secondary: QColor

    def __init__(self,
                 parent: QWidget,
                 header_font: QFont,
                 theme_variables: dict[str, str],
                 source: AbstractEventSource):
        super().__init__(parent)
        self._source = source
        self._period = 'week'
        self._reset_to(self._period)
        self._init_colors(theme_variables)

        file = QFile(":/stats.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._stats_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

        # noinspection PyTypeChecker
        self._header_text = self._stats_window.findChild(QLabel, "statsHeaderText")
        self._header_text.setFont(header_font)

        # noinspection PyTypeChecker
        self._header_subtext = self._stats_window.findChild(QLabel, "statsHeaderSubtext")
        self._period_actions = {
            'year': self._create_checkable_action('year', 'Ctrl+Y'),
            'month6': self._create_checkable_action('month6', 'Ctrl+H'),
            'month': self._create_checkable_action('month', 'Ctrl+M'),
            'week': self._create_checkable_action('week', 'Ctrl+W'),
            'day': self._create_checkable_action('day', 'Ctrl+D'),
        }
        self._period_actions['week'].setChecked(True)
        self._prev_action = self._create_simple_action('prev', self._prev)
        self._prev_action.setShortcut('Left')
        self._next_action = self._create_simple_action('next', self._next)
        self._next_action.setShortcut('Right')

        close_action = QAction('Close', self._stats_window)
        close_action.triggered.connect(self._stats_window.close)
        close_action.setShortcut('Esc')
        self._stats_window.addAction(close_action)

        chart = QChart()
        self._chart = chart
        axis_x = QBarCategoryAxis(self)
        f = axis_x.labelsFont()
        f.setPointSize(round(f.pointSize() * 0.8))
        axis_x.setLabelsFont(f)
        axis_x.setGridLineVisible(False)
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

        self._update_chart('week', self._to)

        # noinspection PyTypeChecker
        layout: QVBoxLayout = self._stats_window.findChild(QVBoxLayout, "statsGraph")
        view = QChartView(chart, self._stats_window)
        view.setObjectName('statsView')
        view.setRenderHint(QPainter.RenderHint.Antialiasing)

        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)
        layout.addWidget(view)

    def _init_colors(self, theme_variables: dict[str, str]) -> None:
        self._color_primary = QColor(theme_variables['TABLE_TEXT_COLOR'])
        self._color_secondary = QColor(theme_variables['SELECTION_BG_COLOR'])
        self._color_highlight = QColor(theme_variables['FOCUS_TEXT_COLOR'])

    def _style_chart(self) -> None:
        self._bars['finished'].setColor(QColor('dodgerblue'))
        self._bars['startable'].setColor(QColor('lightgray'))
        self._bars['canceled'].setColor(QColor('orangered'))

        self._bars['finished'].setBorderColor(self._color_highlight)
        self._bars['startable'].setBorderColor(self._color_highlight)
        self._bars['canceled'].setBorderColor(self._color_highlight)

        self._chart.legend().setLabelColor(self._color_primary)
        self._axis_x.setLabelsColor(QColor(self._color_primary))
        self._axis_y.setLabelsColor(QColor(self._color_primary))

        self._axis_y.setGridLineColor(QColor(self._color_secondary))

    def _time_delta_for_period(self, period: str, date: datetime.datetime, left: bool):
        date = StatsWindow._drop_time(date, period, True)
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

    @staticmethod
    def _drop_time(date: datetime.datetime, period: str, start: bool):
        if period == 'week':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     0 if start else 23,
                                     0 if start else 59,
                                     0 if start else 59,
                                     tzinfo=date.tzinfo)
        elif period == 'year':
            return datetime.datetime(date.year,
                                     date.month,
                                     monthrange(date.year, date.month)[1],
                                     0 if start else 23,
                                     0 if start else 59,
                                     0 if start else 59,
                                     tzinfo=date.tzinfo)
        elif period == 'day':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     date.hour,
                                     0 if start else 59,
                                     tzinfo=date.tzinfo)
        elif period == 'month':
            return datetime.datetime(date.year,
                                     date.month,
                                     date.day,
                                     0 if start else 23,
                                     0 if start else 59,
                                     0 if start else 59,
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
        self._to = StatsWindow._drop_time(self._to, self._period, False)
        self._to += self._substep_delta_for_period(self._period, self._to, True)
        self._update_chart(self._period, self._to)

    def _next(self):
        self._to = StatsWindow._drop_time(self._to, self._period, False)
        self._to += self._substep_delta_for_period(self._period, self._to, False)
        self._update_chart(self._period, self._to)

    @staticmethod
    def _format_date(date: datetime.datetime):
        return date.strftime('%d %b %Y, %H:%M')

    def _update_chart(self, period: str, to: datetime.datetime) -> None:
        self._period = period
        _from: datetime.datetime = (to +
                                    self._time_delta_for_period(period, to, True) +
                                    datetime.timedelta(minutes=1))
        header_subtext = f'Average over {StatsWindow._format_date(_from)} to {StatsWindow._format_date(to)}'
        self._header_subtext.setText(header_subtext)

        d = self.extract_data(period, _from, to)

        completed_count = sum(d[1])
        total_count = completed_count + sum(d[2]) + sum(d[3])
        if total_count > 0:
            completion = round(100 * completed_count / total_count)
            header_text = f'Completed {completed_count} out of {total_count} ({completion}%)'
        else:
            header_text = 'No data'
        self._header_text.setText(header_text)

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

        self._style_chart()

    def _create_checkable_action(self, name: str, shortcut: str) -> QAction:
        # noinspection PyTypeChecker
        button: QToolButton = self._stats_window.findChild(QToolButton, name)
        action = QAction(button.text(), self)
        action.setCheckable(True)
        action.setShortcut(shortcut)
        button.setDefaultAction(action)
        action.triggered.connect(lambda: self.select_period(name))
        return action

    def _create_simple_action(self, name: str, callback: Callable) -> QAction:
        # noinspection PyTypeChecker
        button: QToolButton = self._stats_window.findChild(QToolButton, name)
        action = QAction(button.text(), self)
        button.setDefaultAction(action)
        action.triggered.connect(callback)
        return action

    def _reset_to(self, period):
        self._to = StatsWindow._drop_time(datetime.datetime.now(datetime.timezone.utc).astimezone(), period, False)

    def select_period(self, period: str) -> None:
        for name in self._period_actions:
            action = self._period_actions[name]
            action.setChecked(name == period)
        self._reset_to(period)
        self._update_chart(period, self._to)

    @staticmethod
    def _rotate(lst: list, n: int) -> list:
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
            rotate_around = period_to.hour
        elif group == 'month':
            cats = [str(i + 1) for i in range(31)]
            rotate_around = period_to.day - 1
        elif group == 'month6':
            cats = [str(i + 1) for i in range(53)]
            rotate_around = period_to.isocalendar()[1] - 1
        else:
            raise Exception(f'Grouping by {group} is not implemented')

        list_finished = [0 for _ in cats]
        list_canceled = list_finished.copy()
        list_ready = list_finished.copy()
        list_total = list_finished.copy()

        for p in self._source.pomodoros():
            finished = p.is_finished()
            canceled = len(p) > 0
            if finished or canceled:
                when = p.get_last_modified_date().astimezone()
            else:
                when = p.get_create_date().astimezone()
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
                index = when.hour
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

        r = [StatsWindow._rotate(cats, rotate_around),
             StatsWindow._rotate(list_finished, rotate_around),
             StatsWindow._rotate(list_canceled, rotate_around),
             StatsWindow._rotate(list_ready, rotate_around),
             StatsWindow._rotate(list_total, rotate_around)]

        if group == 'month6':
            # Truncate to half a year
            r[0] = r[0][26:]
            r[1] = r[1][26:]
            r[2] = r[2][26:]
            r[3] = r[3][26:]
            r[4] = r[4][26:]

        return r

    def show(self):
        self._stats_window.show()

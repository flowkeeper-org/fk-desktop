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

    _series: QStackedBarSeries
    _axis_x: QBarCategoryAxis
    _axis_y: QValueAxis
    _bars: dict[str, QBarSet]

    def __init__(self, parent: QWidget, application: QApplication, source: AbstractEventSource):
        super().__init__(parent)
        self._source = source

        file = QFile(":/stats.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._stats_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

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

        self._update_chart('week')

        layout: QVBoxLayout = self._stats_window.findChild(QVBoxLayout, "statsGraph")
        view = QChartView(chart, self._stats_window)
        view.setObjectName('statsView')
        chart.setTheme(QChart.ChartTheme.ChartThemeDark if application.is_dark_theme() else QChart.ChartTheme.ChartThemeLight)
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)
        layout.addWidget(view)

        self._header_text = self._stats_window.findChild(QLabel, "statsHeaderText")
        self._header_text.setFont(application.get_header_font())

        self._header_subtext = self._stats_window.findChild(QLabel, "statsHeaderSubtext")
        self._period_actions = {
            'year': self._create_action('year'),
            'month6': self._create_action('month6'),
            'month': self._create_action('month'),
            'week': self._create_action('week'),
            'day': self._create_action('day'),
        }
        self._period_actions['week'].setChecked(True)

    def _update_chart(self, period: str) -> None:
        d = self.extract_data(period)
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

    def _create_action(self, name: str) -> QAction:
        button: QToolButton = self._stats_window.findChild(QToolButton, name)
        action = QAction(button.text(), self)
        action.setCheckable(True)
        button.setDefaultAction(action)
        action.triggered.connect(lambda: self.select_period(name))
        return action

    def select_period(self, period: str) -> None:
        for name in self._period_actions:
            action = self._period_actions[name]
            action.setChecked(name == period)
        self._update_chart(period)

    def extract_data(self, group: str):
        if group == 'week':
            cats = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        elif group == 'year':
            cats = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        elif group == 'day':
            cats = [str(i) for i in range(24)]
        elif group == 'month':
            cats = [str(i + 1) for i in range(31)]
        elif group == 'month6':
            cats = [str(i + 1) for i in range(53)]
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
            if group == 'week':
                index = when.weekday()
            elif group == 'year':
                index = when.month - 1
            elif group == 'day':
                index = when.hour - 1
            elif group == 'month':
                index = when.day - 1
            elif group == 'month6':
                index = when.isocalendar()[1]

            if finished:
                list_finished[index] += 1
            elif canceled:
                list_canceled[index] += 1
            else:
                list_ready[index] += 1
            list_total[index] += 1

        return cats, list_finished, list_canceled, list_ready, list_total

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

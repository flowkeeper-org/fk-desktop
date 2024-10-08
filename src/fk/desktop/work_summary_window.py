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
import csv
import datetime
import pathlib
from abc import ABC, abstractmethod
from io import StringIO
from os import path

from PySide6 import QtUiTools
from PySide6.QtCore import QObject, QFile
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QWidget, QTextEdit, \
    QCheckBox, QComboBox, QDialogButtonBox, QMessageBox

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.pomodoro import Pomodoro
from fk.desktop.settings import SettingsDialog
from fk.qt.oauth import open_url


def _format_date(date: datetime.datetime):
    return date.strftime('%d %b %Y')


class Formatter(ABC):
    @abstractmethod
    def header(self) -> str:
        pass

    @abstractmethod
    def week(self, text: str) -> str:
        pass

    @abstractmethod
    def day(self, text: str) -> str:
        pass

    @abstractmethod
    def workitem(self, text: str, duration: datetime.timedelta = None) -> str:
        pass


class MarkdownFormatter(Formatter):
    def header(self) -> str:
        return f'# Work summary\n'

    def week(self, text: str) -> str:
        return f'\n## {text}\n'

    def day(self, text: str) -> str:
        return f'\n### {text}\n\n'

    def workitem(self, text: str, duration: datetime.timedelta = None) -> str:
        if duration is None:
            return f' - {text}\n'
        else:
            return f' - {text}: {duration}\n'


class PlaintextFormatter(Formatter):
    def header(self) -> str:
        return ''

    def week(self, text: str) -> str:
        return f'\n*** {text} ***\n'

    def day(self, text: str) -> str:
        return f'\n{text}\n\n'

    def workitem(self, text: str, duration: datetime.timedelta = None) -> str:
        if duration is None:
            return f'{text}\n'
        else:
            return f'{text}: {duration}\n'


class CsvFormatter(Formatter):
    _last_week: str  # With those we rely on the correct order of those formatting instructions
    _last_day: str

    def __init__(self):
        self._last_week = ''
        self._last_day = ''

    def header(self) -> str:
        f = StringIO()
        # TODO: It would be more efficient and elegant, if we used streams throughout this entire file
        #  instead of string concatenation
        csv.writer(f).writerow(['Week number', 'Date', 'Work item', 'Time spent'])
        return f.getvalue()

    def week(self, text: str) -> str:
        self._last_week = text
        return ''

    def day(self, text: str) -> str:
        self._last_day = text
        return ''

    def workitem(self, text: str, duration: datetime.timedelta = None) -> str:
        f = StringIO()
        csv.writer(f).writerow([self._last_week,
                                self._last_day,
                                text,
                                duration if duration is not None else ""])
        return f.getvalue()


class WorkSummaryWindow(QObject):
    _source: AbstractEventSource
    _summary_window: QMainWindow
    _data: dict[datetime.date, dict[str, datetime.timedelta]]
    _results: QTextEdit
    _view_time_spent: QCheckBox
    _format: QComboBox
    _buttons: QDialogButtonBox

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__(parent)
        self._source = source

        file = QFile(":/summary.ui")
        file.open(QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        self._summary_window: QMainWindow = QtUiTools.QUiLoader().load(file, parent)
        file.close()

        self._buttons: QDialogButtonBox = self._summary_window.findChild(QDialogButtonBox, "buttons")
        self._buttons.clicked.connect(lambda btn: self._on_action(self._buttons.buttonRole(btn)))

        self._results: QTextEdit = self._summary_window.findChild(QTextEdit, "results")

        self._view_time_spent: QCheckBox = self._summary_window.findChild(QCheckBox, "view_time_spent")
        self._view_time_spent.stateChanged.connect(lambda v: self._display_formatted())

        self._format: QComboBox = self._summary_window.findChild(QComboBox, "format")
        self._format.addItems(['Markdown',
                               'Formatted',
                               'Plaintext',
                               'CSV'])
        self._format.currentIndexChanged.connect(lambda v: self._display_formatted())

        close_action = QAction(self._summary_window, 'Close')
        close_action.triggered.connect(self._summary_window.close)
        close_action.setShortcut('Esc')
        self._summary_window.addAction(close_action)

        self._data = self._extract_data()
        self._display_formatted()

    def _extract_data(self) -> dict[datetime.date, dict[str, datetime.timedelta]]:
        data = dict[datetime.date, dict[str, datetime.timedelta]]()
        for w in self._source.workitems():
            if w.is_sealed():
                key = w.get_last_modified_date().date()  # That's when it was sealed
                if key not in data:
                    data[key] = dict()
                workitems = data[key]
                if w.get_name() not in workitems:
                    workitems[w.get_name()] = datetime.timedelta()
            for p in w.values():
                pp: Pomodoro = p
                if pp.is_finished():
                    key = pp.get_last_modified_date().date()  # That's when it was finished
                    if key not in data:
                        data[key] = dict()
                    workitems = data[key]
                    if w.get_name() not in workitems:
                        workitems[w.get_name()] = datetime.timedelta()
                    workitems[w.get_name()] += datetime.timedelta(seconds=pp.get_work_duration())
        return data

    def _display_formatted(self) -> None:
        res = self._format_data(self._view_time_spent.isChecked())
        if self._format.currentText() == 'Formatted':
            self._results.setMarkdown(res)
        else:
            self._results.setText(res)

    def _format_data(self, include_time: bool) -> str:
        # First sort the dates / keys
        dates = list(self._data.keys())
        dates.sort(reverse=True)

        # Then group dates by weeks
        weeks = dict[str, list[datetime.date]]()
        for date in dates:
            week_number = date.isocalendar()[1]
            # Those keys are sortable alphabetically
            week_key = f'{date.year}, Week {"0" if week_number < 10 else ""}{week_number}'
            if week_key not in weeks:
                weeks[week_key] = list()
            weeks[week_key].append(date)    # We know they don't repeat

        weeks_sorted = list(weeks.keys())
        weeks_sorted.sort(reverse=True)

        # Get correct formatter
        format_name: str = self._format.currentText()

        if format_name == 'Markdown' or format_name == 'Formatted':
            formatter = MarkdownFormatter()
        elif format_name == 'CSV':
            formatter = CsvFormatter()
        else:
            formatter = PlaintextFormatter()

        # Now iterate through the groups and format
        res = formatter.header()
        for week in weeks_sorted:
            res += formatter.week(week)
            for date in weeks[week]:
                res += formatter.day(str(date))
                workitems = self._data[date]
                for workitem_name in workitems:
                    duration = workitems[workitem_name]
                    if include_time:
                        res += formatter.workitem(workitem_name, duration)
                    else:
                        res += formatter.workitem(workitem_name)
        return res

    def show(self):
        self._summary_window.show()

    def _get_file_extension(self) -> str:
        format_name: str = self._format.currentText()
        if format_name == 'Markdown' or format_name == 'Formatted':
            return 'md'
        elif format_name == 'CSV':
            return 'csv'
        else:
            return 'txt'

    def _export_to_file(self, filename: str):
        if path.isdir(filename):
            filename = path.join(filename, f'work-summary.{self._get_file_extension()}')
        res = self._format_data(self._view_time_spent.isChecked())
        with open(filename, "w") as file:
            file.write(res)
        if QMessageBox().information(
                self._summary_window,
                'Success',
                f'Summary is saved to {filename}.\n'
                f'Would you like to open the resulting file?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Close) == QMessageBox.StandardButton.Yes:
            open_url(pathlib.Path(path.abspath(filename)).as_uri())

    def _on_action(self, role: QDialogButtonBox.ButtonRole):
        if role == QDialogButtonBox.ButtonRole.AcceptRole:
            SettingsDialog.do_browse_simple('', self._export_to_file)
        elif role == QDialogButtonBox.ButtonRole.RejectRole:
            self._summary_window.close()

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
import json
import pathlib
from abc import ABC, abstractmethod
from io import StringIO
from os import path
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

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

    def workitem_plaintext(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        if duration is not None:
            text += f': {duration}'
        if backlogs is not None and len(backlogs) > 0:
            text += f''', in backlog{"s" if len(backlogs) > 1 else ""} "{'", "'.join(backlogs)}"'''
        return text

    @abstractmethod
    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        pass

    @abstractmethod
    def footer(self) -> str:
        pass


class MarkdownFormatter(Formatter):
    def header(self) -> str:
        return f'# Work summary\n'

    def week(self, text: str) -> str:
        return f'\n## {text}\n'

    def day(self, text: str) -> str:
        return f'\n### {text}\n\n'

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        return f' - {self.workitem_plaintext(text, duration, backlogs)}\n'

    def footer(self) -> str:
        return ''


class OrgModeFormatter(Formatter):
    def header(self) -> str:
        return f'#+title:  Work Summary\n' \
               f'#+author: Flowkeeper\n' \
               f'#+date:   {str(datetime.date.today())}\n' \
               f'\n' \
               f'* Work summary\n'

    def week(self, text: str) -> str:
        return f'** {text}\n'

    def day(self, text: str) -> str:
        return f'*** {text}\n'

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        return f'- {self.workitem_plaintext(text, duration, backlogs)}\n'

    def footer(self) -> str:
        return ''


class MarkdownTableFormatter(Formatter):
    _last_week: str  # With those we rely on the correct order of those formatting instructions
    _last_day: str

    def __init__(self):
        self._last_week = ''
        self._last_day = ''

    def header(self) -> str:
        return '| Week number | Date | Work item | Time spent | Backlogs |\n' \
               '| ----------- | ---- | --------- | ---------- | -------- |\n'

    def week(self, text: str) -> str:
        self._last_week = text
        return ''

    def day(self, text: str) -> str:
        self._last_day = text
        return ''

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        return f'| {self._last_week} | {self._last_day} | {text} | {duration if duration is not None else ""} | {", ".join(backlogs) if backlogs is not None else ""} |\n'

    def footer(self) -> str:
        return ''


class PlaintextFormatter(Formatter):
    def header(self) -> str:
        return ''

    def week(self, text: str) -> str:
        return f'\n*** {text} ***\n'

    def day(self, text: str) -> str:
        return f'\n{text}\n\n'

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        return self.workitem_plaintext(text, duration, backlogs) + '\n'

    def footer(self) -> str:
        return ''


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
        csv.writer(f).writerow(['Week number', 'Date', 'Work item', 'Time spent', 'Backlogs'])
        return f.getvalue()

    def week(self, text: str) -> str:
        self._last_week = text
        return ''

    def day(self, text: str) -> str:
        self._last_day = text
        return ''

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        f = StringIO()
        csv.writer(f).writerow([self._last_week,
                                self._last_day,
                                text,
                                duration if duration is not None else "",
                                ('"' + '", "'.join(backlogs) + '"') if backlogs is not None and len(backlogs) > 0 else ""])
        return f.getvalue()

    def footer(self) -> str:
        return ''


class JsonFormatter(Formatter):
    _json: dict
    _last_week: str
    _last_day: str

    def __init__(self):
        self._json = dict()
        self._last_week = ''
        self._last_day = ''

    def header(self) -> str:
        self._json['weeks'] = dict()
        return ''

    def week(self, text: str) -> str:
        self._json['weeks'][text] = {}
        self._last_week = text
        return ''

    def day(self, text: str) -> str:
        self._json['weeks'][self._last_week][text] = []
        self._last_day = text
        return ''

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        to_append = {"title": text}
        if duration is not None:
            to_append['duration'] = str(duration)
        if backlogs is not None:
            to_append['backlogs'] = list(backlogs)
        self._json['weeks'][self._last_week][self._last_day].append(to_append)
        return ''

    def footer(self) -> str:
        return json.dumps(self._json, indent=2)


class XmlFormatter(Formatter):
    _xml: Element
    _last_week: Element
    _last_day: Element

    def __init__(self):
        self._xml = Element('weeks')
        self._last_week = ''
        self._last_day = ''

    def header(self) -> str:
        return ''

    def week(self, text: str) -> str:
        el = Element('week', name=text)
        self._xml.append(el)
        self._last_week = el
        return ''

    def day(self, text: str) -> str:
        el = Element('day', date=text)
        self._last_week.append(el)
        self._last_day = el
        return ''

    def workitem(self, text: str, duration: datetime.timedelta = None, backlogs: set[str] = None) -> str:
        el = Element('item', title=text)
        if duration is not None:
            el.attrib['duration'] = str(duration)
        if backlogs is not None and len(backlogs) > 0:
            bs = Element('backlogs')
            el.append(bs)
            for backlog in backlogs:
                bs.append(Element('backlog', title=backlog))
        self._last_day.append(el)
        return ''

    def footer(self) -> str:
        ElementTree.indent(self._xml)
        return ElementTree.tostring(self._xml, encoding='utf8').decode('utf8')


class WorkSummaryWindow(QObject):
    _source: AbstractEventSource
    _summary_window: QMainWindow
    _data: dict[datetime.date, dict[str, list[datetime.timedelta, set[str]]]]
    _results: QTextEdit
    _view_durations: QCheckBox
    _view_backlogs: QCheckBox
    _format: QComboBox
    _period: QComboBox
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

        self._results: QTextEdit = self._summary_window.findChild(QTextEdit, "work_summary_results")

        self._view_durations: QCheckBox = self._summary_window.findChild(QCheckBox, "view_time_spent")
        self._view_durations.stateChanged.connect(lambda v: self._display_formatted())
        self._view_durations.stateChanged.connect(self._save_settings)

        self._view_backlogs: QCheckBox = self._summary_window.findChild(QCheckBox, "view_backlogs")
        self._view_backlogs.stateChanged.connect(lambda v: self._display_formatted())
        self._view_backlogs.stateChanged.connect(self._save_settings)

        self._format: QComboBox = self._summary_window.findChild(QComboBox, "format")
        self._format.addItems(['Markdown',
                               'Markdown table',
                               'Emacs Org Mode',
                               'Formatted',
                               'Formatted table',
                               'Plaintext',
                               'CSV',
                               'JSON',
                               'XML'])
        self._format.currentIndexChanged.connect(lambda v: self._display_formatted())
        self._format.currentIndexChanged.connect(self._save_settings)

        self._period: QComboBox = self._summary_window.findChild(QComboBox, "period")
        self._period.addItems(['Everything',
                               'This week',
                               'Previous week',
                               'Today',
                               'Yesterday',
                               'Last working day (Mon - Fri)'])
        self._period.currentIndexChanged.connect(lambda v: self._display_formatted())
        self._period.currentIndexChanged.connect(self._save_settings)

        self._load_settings()

        close_action = QAction(self._summary_window, 'Close')
        close_action.triggered.connect(self._summary_window.close)
        close_action.setShortcut('Esc')
        self._summary_window.addAction(close_action)

        self._data = self._extract_data()
        self._display_formatted()

    def _save_settings(self):
        self._source.get_settings().set({
            "Application.work_summary_settings": json.dumps({
                "format": self._format.currentIndex(),
                "period": self._period.currentIndex(),
                "durations": self._view_durations.isChecked(),
                "backlogs": self._view_backlogs.isChecked(),
            })
        })

    def _load_settings(self):
        s = json.loads(self._source.get_settings().get("Application.work_summary_settings"))

        self._format.blockSignals(True)
        self._format.setCurrentIndex(s.get('format', 0))
        self._format.blockSignals(False)

        self._period.blockSignals(True)
        self._period.setCurrentIndex(s.get('period', 0))
        self._period.blockSignals(False)

        self._view_durations.blockSignals(True)
        self._view_durations.setChecked(s.get('durations', False))
        self._view_durations.blockSignals(False)

        self._view_backlogs.blockSignals(True)
        self._view_backlogs.setChecked(s.get('backlogs', False))
        self._view_backlogs.blockSignals(False)

    def _extract_data(self) -> dict[datetime.date, dict[str, list[datetime.timedelta, set[str]]]]:
        data = dict[datetime.date, dict[str, list[datetime.timedelta, set[str]]]]()
        for w in self._source.workitems():
            if w.is_sealed():
                key = w.get_last_modified_date().date()  # That's when it was sealed
                if key not in data:
                    data[key] = dict()
                workitems = data[key]
                if w.get_name() not in workitems:
                    workitems[w.get_name()] = [datetime.timedelta(), set()]
                workitems[w.get_name()][1].add(w.get_parent().get_name())
            for p in w.values():
                pp: Pomodoro = p
                if pp.is_finished():
                    key = pp.get_last_modified_date().date()  # That's when it was finished
                    if key not in data:
                        data[key] = dict()
                    workitems = data[key]
                    if w.get_name() not in workitems:
                        workitems[w.get_name()] = [datetime.timedelta(), set([w.get_parent().get_name()])]
                    workitems[w.get_name()][0] += datetime.timedelta(seconds=pp.get_work_duration())
                    workitems[w.get_name()][1].add(w.get_parent().get_name())
        return data

    def _display_formatted(self) -> None:
        res = self._format_data(self._view_durations.isChecked(), self._view_backlogs.isChecked())
        if self._format.currentText() == 'Formatted' or self._format.currentText() == 'Formatted table':
            self._results.setMarkdown(res)
        else:
            self._results.setText(res)

    def _format_data(self, include_durations: bool, include_backlogs: bool) -> str:
        # Get the period
        period: str = self._period.currentText()

        # First sort the dates / keys
        dates = list(self._data.keys())
        dates.sort(reverse=True)

        # Prepare for period filtering
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        this_week = today.isocalendar()[1]
        if today.weekday() == 6:
            last_working_day = today - datetime.timedelta(days=2)
        elif today.weekday() == 5:
            last_working_day = today - datetime.timedelta(days=1)
        else:
            last_working_day = today
        if this_week == 1:
            previous_week = 52
            year_of_previous_week = today.year - 1
        else:
            previous_week = this_week - 1
            year_of_previous_week = today.year

        # Then group dates by weeks
        weeks = dict[str, list[datetime.date]]()
        for date in dates:
            week_number = date.isocalendar()[1]

            # Period filtering
            if period == 'Today' and date != today:
                continue
            elif period == 'Yesterday' and date != yesterday:
                continue
            elif period == 'This week' and (week_number != this_week or date.year != today.year):
                continue
            elif period == 'Previous week' and (week_number != previous_week or date.year != year_of_previous_week):
                continue
            elif period == 'Last working day (Mon - Fri)' and date != last_working_day:
                continue

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
        elif format_name == 'Markdown table' or format_name == 'Formatted table':
            formatter = MarkdownTableFormatter()
        elif format_name == 'CSV':
            formatter = CsvFormatter()
        elif format_name == 'JSON':
            formatter = JsonFormatter()
        elif format_name == 'XML':
            formatter = XmlFormatter()
        elif format_name == 'Emacs Org Mode':
            formatter = OrgModeFormatter()
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
                    duration = workitems[workitem_name][0]
                    backlogs = workitems[workitem_name][1]
                    res += formatter.workitem(workitem_name,
                                              duration if include_durations else None,
                                              backlogs if include_backlogs else None)
        res += formatter.footer()
        return res

    def show(self):
        self._summary_window.show()

    def _get_file_extension(self) -> str:
        format_name: str = self._format.currentText()
        if format_name == 'Markdown' or \
                format_name == 'Formatted' or \
                format_name == 'Markdown table' or \
                format_name == 'Formatted table':
            return 'md'
        elif format_name == 'CSV':
            return 'csv'
        elif format_name == 'JSON':
            return 'json'
        elif format_name == 'XML':
            return 'xml'
        elif format_name == 'Emacs Org Mode':
            return 'org'
        else:
            return 'txt'

    def _export_to_file(self, filename: str):
        if path.isdir(filename):
            filename = path.join(filename, f'work-summary.{self._get_file_extension()}')
        res = self._format_data(self._view_durations.isChecked(), self._view_backlogs.isChecked())
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

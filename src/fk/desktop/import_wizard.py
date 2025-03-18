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
import logging
import os
from collections.abc import Callable

from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QWizard, QCheckBox, QLineEdit, \
    QHBoxLayout, QPushButton, QProgressBar, QWidget, QRadioButton, QTextEdit, QComboBox

from fk.core.event_source_holder import EventSourceHolder
from fk.core.import_export import import_, import_github_issues, import_simple
from fk.core.sandbox import get_sandbox_type
from fk.desktop.settings import SettingsDialog

logger = logging.getLogger(__name__)


class PageImportIntro(QWizardPage):
    from_file: QRadioButton
    from_csv: QRadioButton
    from_github: QRadioButton
    from_gitlab: QRadioButton
    from_jira: QRadioButton
    from_trello: QRadioButton
    from_ms_todo: QRadioButton
    from_google_tasks: QRadioButton
    from_todoist: QRadioButton
    from_ticktick: QRadioButton

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        label = QLabel("This wizard will help you import Flowkeeper data.", self)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.from_file = QRadioButton('Import from Flowkeeper data file or backup', self)
        layout.addWidget(self.from_file)

        self.from_csv = QRadioButton('Import from CSV', self)
        layout.addWidget(self.from_csv)

        self.from_github = QRadioButton('Import from GitHub', self)
        layout.addWidget(self.from_github)

        self.from_gitlab = QRadioButton('Import from GitLab', self)
        self.from_gitlab.setDisabled(True)
        layout.addWidget(self.from_gitlab)

        self.from_jira = QRadioButton('Import from JIRA', self)
        self.from_jira.setDisabled(True)
        layout.addWidget(self.from_jira)

        self.from_trello = QRadioButton('Import from Trello', self)
        self.from_trello.setDisabled(True)
        layout.addWidget(self.from_trello)

        self.from_ms_todo = QRadioButton('Import from Microsoft To Do', self)
        self.from_ms_todo.setDisabled(True)
        layout.addWidget(self.from_ms_todo)

        self.from_google_tasks = QRadioButton('Import from Google Tasks', self)
        self.from_google_tasks.setDisabled(True)
        layout.addWidget(self.from_google_tasks)

        self.from_todoist = QRadioButton('Import from Todoist', self)
        self.from_todoist.setDisabled(True)
        layout.addWidget(self.from_todoist)

        self.from_ticktick = QRadioButton('Import from TickTick', self)
        self.from_ticktick.setDisabled(True)
        layout.addWidget(self.from_ticktick)

        self.from_file.setChecked(True)
        self.setLayout(layout)

    def get_selected_import_type(self) -> str:
        if self.from_file.isChecked():
            return 'file'
        elif self.from_github.isChecked():
            return 'github'
        elif self.from_csv.isChecked():
            return 'csv'
        else:
            return 'other'


class PageImportSettings(QWizardPage):
    get_type: Callable[[], str]

    import_location: QLineEdit | None
    import_repo: QLineEdit | None
    import_token: QLineEdit | None
    import_delimiter: QComboBox | None
    import_skip_header: QCheckBox | None
    import_ignore_errors: QCheckBox | None
    import_type_smart: QRadioButton | None
    import_type_replay: QRadioButton | None

    tag_creator: QCheckBox | None
    tag_assignee: QCheckBox | None
    tag_labels: QCheckBox | None
    tag_milestone: QCheckBox | None
    tag_state: QCheckBox | None

    def isComplete(self):
        import_type = self.get_type()
        if import_type in ['file', 'csv']:
            return len(self.import_location.text().strip()) > 0
        elif import_type == 'github':
            return len(self.import_repo.text().strip()) > 0
        else:
            return False

    def __init__(self, get_type: Callable[[], str]):
        super().__init__()
        self.get_type = get_type
        self._reset()

    def _reset(self):
        self.import_location = None
        self.import_repo = None
        self.import_token = None
        self.import_delimiter = None
        self.import_skip_header = None
        self.import_ignore_errors = None
        self.import_type_smart = None
        self.import_type_replay = None
        self.tag_creator = None
        self.tag_assignee = None
        self.tag_labels = None
        self.tag_milestone = None
        self.tag_state = None
        for child in self.children():
            child.deleteLater()

    def cleanupPage(self):
        self._reset()

    def initializePage(self):
        layout_v = QVBoxLayout(self)
        self.setLayout(layout_v)

        import_type = self.get_type()
        if import_type == 'file':
            self._init_for_file(layout_v)
        elif import_type == 'csv':
            self._init_for_csv(layout_v)
        elif import_type == 'github':
            self._init_for_github(layout_v)
        else:
            self._init_for_other(layout_v)

        self.setCommitPage(True)
        self.setButtonText(QWizard.WizardButton.CommitButton, 'Start')

    def _init_for_file(self, layout_v):
        label = QLabel("Select source file", self)
        label.setWordWrap(True)
        layout_v.addWidget(label)

        layout_h = QHBoxLayout()
        layout_v.addLayout(layout_h)

        self.import_location = QLineEdit(self)
        self.import_location.setPlaceholderText('Import filename')
        self.import_location.textChanged.connect(lambda s: self.completeChanged.emit())
        layout_h.addWidget(self.import_location)

        if get_sandbox_type() is not None:
            # Force the user to use the XDG portal-aware file chooser
            self.import_location.setDisabled(True)

        import_location_browse = QPushButton("Browse...", self)
        import_location_browse.clicked.connect(lambda: SettingsDialog.do_browse(self.import_location))
        layout_h.addWidget(import_location_browse)

        self.import_ignore_errors = QCheckBox('Ignore errors and continue', self)
        self.import_ignore_errors.setDisabled(False)
        layout_v.addWidget(self.import_ignore_errors)

        self.import_type_smart = QRadioButton("Smart import - safe option, data is appended or renamed", self)
        self.import_type_smart.setChecked(True)
        layout_v.addWidget(self.import_type_smart)

        self.import_type_replay = QRadioButton("Replay imported history - can result in duplicates or deletions", self)
        layout_v.addWidget(self.import_type_replay)

    def _init_for_csv(self, layout_v):
        label = QLabel('Select CSV file. Note that the data should have exactly three columns -- '
                       'backlog name, task name, and state ("new" or "completed").', self)
        label.setWordWrap(True)
        layout_v.addWidget(label)

        layout_h = QHBoxLayout()
        layout_v.addLayout(layout_h)

        self.import_location = QLineEdit(self)
        self.import_location.setPlaceholderText('Import filename')
        self.import_location.textChanged.connect(self.completeChanged)
        layout_h.addWidget(self.import_location)

        if get_sandbox_type() is not None:
            # Force the user to use the XDG portal-aware file chooser
            self.import_location.setDisabled(True)

        import_location_browse = QPushButton("Browse...", self)
        import_location_browse.clicked.connect(lambda: SettingsDialog.do_browse(self.import_location))
        layout_h.addWidget(import_location_browse)

        self.import_skip_header = QCheckBox('Skip header (first row)', self)
        self.import_skip_header.setChecked(False)
        layout_v.addWidget(self.import_skip_header)

        self.import_delimiter = QComboBox(self)
        self.import_delimiter.addItems(['Columns are separated by comma (,)',
                                        'Columns are separated by semicolon (;)',
                                        'Columns are separated by tab (\\t)'])
        layout_v.addWidget(self.import_delimiter)

    def _init_for_github(self, layout_v):
        label = QLabel("Enter a GitHub owner/repository pair", self)
        label.setWordWrap(True)
        layout_v.addWidget(label)

        self.import_repo = QLineEdit(self)
        self.import_repo.setPlaceholderText('Example: flowkeeper-org/fk-desktop')
        self.import_repo.textChanged.connect(lambda s: self.completeChanged.emit())
        layout_v.addWidget(self.import_repo)

        label = QLabel("GitHub API token (for private repos only)", self)
        label.setWordWrap(True)
        layout_v.addWidget(label)

        self.import_token = QLineEdit(self)
        layout_v.addWidget(self.import_token)

        self.tag_state = QCheckBox('Create tags for issue state', self)
        self.tag_state.setChecked(False)
        layout_v.addWidget(self.tag_state)

        self.tag_assignee = QCheckBox('Create tags for issue assignee', self)
        self.tag_assignee.setChecked(False)
        layout_v.addWidget(self.tag_assignee)

        self.tag_creator = QCheckBox('Create tags for issue creator', self)
        self.tag_creator.setChecked(False)
        layout_v.addWidget(self.tag_creator)

        self.tag_labels = QCheckBox('Create tags for issue labels', self)
        self.tag_labels.setChecked(True)
        layout_v.addWidget(self.tag_labels)

        self.tag_milestone = QCheckBox('Create tags for issue milestone', self)
        self.tag_milestone.setChecked(True)
        layout_v.addWidget(self.tag_milestone)

    def _init_for_other(self, layout_v):
        label = QLabel("Not implemented, sorry", self)
        label.setWordWrap(True)
        layout_v.addWidget(label)

    def get_settings(self) -> dict[str, any]:
        res = {
            'import_type': self.get_type(),
        }
        if self.import_location is not None:
            res['location'] = self.import_location.text()
        if self.import_repo is not None:
            res['repo'] = self.import_repo.text()
        if self.import_token is not None:
            res['token'] = self.import_token.text()
        if self.import_delimiter is not None:
            res['delimiter'] = self.import_delimiter.currentText()
        if self.import_skip_header is not None:
            res['skip_header'] = self.import_skip_header.isChecked()
        if self.import_ignore_errors is not None:
            res['ignore_errors'] = self.import_ignore_errors.isChecked()
        if self.import_type_smart is not None:
            res['type_smart'] = self.import_type_smart.isChecked()
        if self.import_type_replay is not None:
            res['type_replay'] = self.import_type_replay.isChecked()
        if self.tag_assignee is not None:
            res['tag_assignee'] = self.tag_assignee.isChecked()
        if self.tag_creator is not None:
            res['tag_creator'] = self.tag_creator.isChecked()
        if self.tag_labels is not None:
            res['tag_labels'] = self.tag_labels.isChecked()
        if self.tag_state is not None:
            res['tag_state'] = self.tag_state.isChecked()
        if self.tag_milestone is not None:
            res['tag_milestone'] = self.tag_milestone.isChecked()
        return res


class PageImportProgress(QWizardPage):
    label: QLabel
    log: QTextEdit
    progress: QProgressBar

    _import_complete: bool
    _source_holder: EventSourceHolder
    _get_settings: Callable[[], dict[str, any]]

    def isComplete(self):
        return self._import_complete

    def __init__(self,
                 source_holder: EventSourceHolder,
                 get_settings: Callable[[], dict[str, any]]):
        super().__init__()
        self._import_complete = False
        self._source_holder = source_holder
        self._get_settings = get_settings

    def initializePage(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Data import is in progress. Please do not close this window until it completes.", self)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QTextEdit(self)
        layout.addWidget(self.log)

        self.setLayout(layout)
        self.setFinalPage(True)

        self.start()

    def finish_for_file(self):
        # Repair it, if file source
        repair_result = self._source_holder.get_source().repair()
        if repair_result is not None:
            log = "\n".join(repair_result)
            self.log.setText(f'The result was cleaned up:\n{log}')

        self._source_holder.close_current_source()
        self._source_holder.request_new_source()

    def finish(self, callback: Callable[[], None] | None = None):
        if self.progress.maximum() == 0:
            # This is a subtle workaround to avoid "forever animated" progress bars on Windows
            self.progress.setMaximum(1)
        self.progress.setValue(self.progress.maximum())
        self._import_complete = True
        self.label.setText('Done. You can now close this window.')
        if callback:
            callback()
        self.completeChanged.emit()

    def _import_from_file(self):
        settings = self._get_settings()
        import_(self._source_holder.get_source(),
                settings['location'],
                settings['ignore_errors'],
                settings['type_smart'],
                lambda total: self.progress.setMaximum(total),
                lambda value, total: self.progress.setValue(value),
                lambda total: self.finish(self.finish_for_file))

    def _import_from_csv(self):
        settings = self._get_settings()
        skip_header = settings['skip_header']
        delimiter = settings['delimiter']
        if '(,)' in delimiter:
            delimiter = ','
        elif '(;)' in delimiter:
            delimiter = ';'
        elif '(\\t)' in delimiter:
            delimiter = '\t'
        filename = settings['location']
        self.log.append(f'Importing from {filename} using "{delimiter}" as delimiter.')

        data: dict[str, list[str]] = dict()
        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter, quotechar='"')
            n = 0
            for row in reader:
                n += 1
                if skip_header and n == 1:
                    continue
                if len(row) != 3:
                    self.log.append(
                        f'Fatal error: Unable to read row {n} -- it must have exactly three columns, but we parsed {len(row)} instead.')
                    self.finish()
                    return
                if row[2] not in ['new', 'completed']:
                    self.log.append(
                        f'Fatal error: Unable to read row {n} -- task state must be either "new" or "completed", but was "{row[2]}".')
                    self.finish()
                    return
                backlog = row[0]
                if backlog not in data:
                    data[backlog] = list()
                data[backlog].append([row[1], row[2]])

        log = import_simple(self._source_holder.get_source(),
                            data)
        self.log.append(log)
        self.finish()

    def _import_from_github(self):
        settings = self._get_settings()
        repo = settings['repo']
        url = f'https://api.github.com/repos/{repo}/issues?per_page=100'
        token = settings['token']
        logger.debug(f'Will import from GitHub at {repo}')

        def process_response(data: list[object] | None):
            if data is None:
                self.label.setText('ERROR: Cannot get the list of issues from GitHub')
            else:
                log = import_github_issues(self._source_holder.get_source(),
                                           repo,
                                           data,
                                           settings['tag_creator'],
                                           settings['tag_assignee'],
                                           settings['tag_labels'],
                                           settings['tag_milestone'],
                                           settings['tag_state'])
                self.log.append(log)
                self.finish()

        headers = {'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28'}
        if token != '':
            headers['Authorization'] = f'Bearer {token}'

    def start(self):
        import_type = self._get_settings()['import_type']
        if import_type == 'file':
            self._import_from_file()
        elif import_type == 'csv':
            self._import_from_csv()
        elif import_type == 'github':
            self._import_from_github()


class ImportWizard(QWizard):
    page_intro: PageImportIntro
    page_settings: PageImportSettings
    page_progress: PageImportProgress
    _source_holder: EventSourceHolder

    def __init__(self, source_holder: EventSourceHolder, parent: QWidget | None):
        super().__init__(parent)
        self._source_holder = source_holder
        self.setWindowTitle("Import")
        self.page_intro = PageImportIntro()
        self.page_settings = PageImportSettings(self.page_intro.get_selected_import_type)
        self.page_progress = PageImportProgress(source_holder, self.page_settings.get_settings)
        self.addPage(self.page_intro)
        self.addPage(self.page_settings)
        self.addPage(self.page_progress)

        # Account for a Qt bug which shrinks dialogs opened on non-primary displays
        self.setMinimumSize(500, 350)

        if os.name == 'nt':
            # AeroStyle is default on Windows 11, but it looks all white (another Qt bug?) The Classic style looks fine.
            self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)

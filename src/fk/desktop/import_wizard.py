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
from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QWizard, QCheckBox, QLineEdit, \
    QHBoxLayout, QPushButton, QProgressBar, QWidget, QRadioButton

from fk.core.event_source_holder import EventSourceHolder
from fk.core.import_export import import_
from fk.desktop.settings import SettingsDialog


class PageImportIntro(QWizardPage):
    label: QLabel
    layout_v: QVBoxLayout

    def __init__(self):
        super().__init__()
        #self.setTitle("Data import")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("This wizard will help you import Flowkeeper data from file.")
        self.label.setWordWrap(True)
        self.layout_v.addWidget(self.label)
        self.setLayout(self.layout_v)


class PageImportSettings(QWizardPage):
    label: QLabel
    label2: QLabel
    layout_v: QVBoxLayout
    layout_h: QHBoxLayout
    import_location: QLineEdit
    import_location_browse: QPushButton
    import_ignore_errors: QCheckBox

    def isComplete(self):
        return len(self.import_location.text().strip()) > 0

    def __init__(self):
        super().__init__()
        #self.setTitle("Import settings")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("Select source file")
        self.label.setWordWrap(True)
        self.layout_v.addWidget(self.label)
        self.layout_h = QHBoxLayout()
        self.import_location = QLineEdit()
        self.import_location.textChanged.connect(lambda s: self.completeChanged.emit())
        # noinspection PyUnresolvedReferences
        self.import_location.textChanged.connect(lambda s: self.wizard().set_filename(s))
        self.import_location.setPlaceholderText('Import filename')
        self.layout_h.addWidget(self.import_location)
        self.import_location_browse = QPushButton("Browse...")
        self.import_location_browse.clicked.connect(lambda: SettingsDialog.do_browse(self.import_location))
        self.layout_h.addWidget(self.import_location_browse)
        self.layout_v.addLayout(self.layout_h)
        self.import_ignore_errors = QCheckBox('Ignore errors and continue')
        self.import_ignore_errors.setDisabled(False)
        self.layout_v.addWidget(self.import_ignore_errors)
        self.import_type_smart = QRadioButton("Smart import - safe option, data is appended or renamed", self)
        self.import_type_smart.setChecked(True)
        self.layout_v.addWidget(self.import_type_smart)
        self.import_type_replay = QRadioButton("Replay imported history - can result in duplicates or deletions", self)
        self.layout_v.addWidget(self.import_type_replay)
        self.setLayout(self.layout_v)
        self.setCommitPage(True)
        self.setButtonText(QWizard.WizardButton.CommitButton, 'Start')


class PageImportProgress(QWizardPage):
    label: QLabel
    layout_v: QVBoxLayout
    progress: QProgressBar
    _source_holder: EventSourceHolder
    _import_complete: bool
    _filename: str | None
    _ignore_errors: QCheckBox
    _import_type_smart: QRadioButton

    def isComplete(self):
        return self._import_complete

    def __init__(self,
                 source_holder: EventSourceHolder,
                 ignore_errors: QCheckBox,
                 import_type_smart: QRadioButton):
        super().__init__()
        self._import_complete = False
        self._source_holder = source_holder
        self._filename = None
        self._ignore_errors = ignore_errors
        self._import_type_smart = import_type_smart
        #self.setTitle("Importing...")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("Data import is in progress. Please do not close this window until it completes.")
        self.label.setWordWrap(True)
        self.layout_v.addWidget(self.label)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.layout_v.addWidget(self.progress)
        self.setLayout(self.layout_v)
        self.setFinalPage(True)

    def initializePage(self):
        self.start()

    def finish(self):
        self.progress.setValue(self.progress.maximum())
        self._import_complete = True
        self.label.setText('Done. You can now close this window.')
        self._source_holder.request_new_source()
        self.completeChanged.emit()

    def start(self):
        # noinspection PyUnresolvedReferences
        self._filename = self.wizard().option_filename
        import_(self._source_holder.get_source(),
                self._filename,
                self._ignore_errors.isChecked(),
                self._import_type_smart.isChecked(),
                lambda total: self.progress.setMaximum(total),
                lambda value, total: self.progress.setValue(value),
                lambda total: self.finish())


class ImportWizard(QWizard):
    page_intro: PageImportIntro
    page_settings: PageImportSettings
    page_progress: PageImportProgress
    option_filename: str | None
    _source_holder: EventSourceHolder

    def __init__(self, source_holder: EventSourceHolder, parent: QWidget | None):
        super().__init__(parent)
        self._source_holder = source_holder
        self.setWindowTitle("Import")
        self.page_intro = PageImportIntro()
        self.page_settings = PageImportSettings()
        self.page_progress = PageImportProgress(source_holder,
                                                self.page_settings.import_ignore_errors,
                                                self.page_settings.import_type_smart)
        self.addPage(self.page_intro)
        self.addPage(self.page_settings)
        self.addPage(self.page_progress)
        self.option_filename = None

    def set_filename(self, filename):
        self.option_filename = filename

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
import pathlib
import sys
from os import path

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QApplication, QWizard, QCheckBox, QLineEdit, \
    QHBoxLayout, QPushButton, QProgressBar, QWidget

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.file_event_source import FileEventSource
from fk.core.import_export import export
from fk.core.tenant import Tenant
from fk.desktop.settings import SettingsDialog
from fk.qt.qt_settings import QtSettings


class PageExportIntro(QWizardPage):
    label: QLabel
    layout_v: QVBoxLayout

    def __init__(self):
        super().__init__()
        #self.setTitle("Data export")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("This wizard will help you export Flowkeeper data to file.")
        self.label.setWordWrap(True)
        self.layout_v.addWidget(self.label)
        self.setLayout(self.layout_v)


class PageExportSettings(QWizardPage):
    label: QLabel
    label2: QLabel
    layout_v: QVBoxLayout
    layout_h: QHBoxLayout
    export_location: QLineEdit
    export_location_browse: QPushButton
    export_compress: QCheckBox
    export_encrypt: QCheckBox

    def isComplete(self):
        return len(self.export_location.text().strip()) > 0

    def __init__(self, settings: AbstractSettings):
        super().__init__()
        #self.setTitle("Export settings")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("Select destination file")
        self.label.setWordWrap(True)
        self.layout_v.addWidget(self.label)
        self.layout_h = QHBoxLayout()
        self.export_location = QLineEdit()
        self.export_location.textChanged.connect(lambda s: self.completeChanged.emit())
        # noinspection PyUnresolvedReferences
        self.export_location.textChanged.connect(lambda s: self.wizard().set_filename(s))
        self.export_location.setPlaceholderText('Export filename')
        self.layout_h.addWidget(self.export_location)
        self.export_location_browse = QPushButton("Browse...")
        self.export_location_browse.clicked.connect(lambda: SettingsDialog.do_browse(self.export_location))
        self.layout_h.addWidget(self.export_location_browse)
        self.layout_v.addLayout(self.layout_h)
        self.export_compress = QCheckBox('Compress data (delete detailed history)')
        self.export_compress.stateChanged.connect(lambda v: self.wizard().set_compressed(v == 2))
        self.layout_v.addWidget(self.export_compress)
        self.export_encrypt = QCheckBox('Export in plain text (decrypted)')
        if settings.is_e2e_encryption_enabled():
            self.export_encrypt.setEnabled(True)
        else:
            self.export_encrypt.setChecked(True)
            self.export_encrypt.setDisabled(True)
        # noinspection PyUnresolvedReferences
        self.export_encrypt.stateChanged.connect(lambda v: self.wizard().set_encrypted(v != 2))
        self.layout_v.addWidget(self.export_encrypt)
        self.setLayout(self.layout_v)
        self.setCommitPage(True)
        self.setButtonText(QWizard.WizardButton.CommitButton, 'Start')


class PageExportProgress(QWizardPage):
    label: QLabel
    layout_v: QVBoxLayout
    progress: QProgressBar
    _source: AbstractEventSource
    _export_complete: bool
    _filename: str | None

    def isComplete(self):
        return self._export_complete

    def __init__(self, source: AbstractEventSource):
        super().__init__()
        self._export_complete = False
        self._source = source
        self._filename = None
        #self.setTitle("Exporting...")
        self.layout_v = QVBoxLayout()
        self.label = QLabel("Data export is in progress. Please do not close this window until it completes.")
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
        self._export_complete = True
        self.label.setText('Done. You can now close this window.')
        layout_h = QHBoxLayout()
        open_file = QPushButton("Open exported file")
        open_file.clicked.connect(lambda: QDesktopServices.openUrl(
            pathlib.Path(path.abspath(self._filename)).as_uri()))
        layout_h.addWidget(open_file)
        layout_h.addStretch()
        self.layout_v.addLayout(layout_h)
        self.completeChanged.emit()

    def start(self):
        # noinspection PyUnresolvedReferences
        self._filename = self.wizard().option_filename
        export(self._source,
               self._filename,
               Tenant(self._source.get_settings()),
               self.wizard().option_encrypted,
               self.wizard().option_compressed,
               lambda total: self.progress.setMaximum(total),
               lambda value, total: self.progress.setValue(value),
               lambda total: self.finish())


class ExportWizard(QWizard):
    page_intro: PageExportIntro
    page_settings: PageExportSettings
    page_progress: PageExportProgress
    option_filename: str | None
    option_compressed: bool
    option_encrypted: bool
    _source: AbstractEventSource

    def __init__(self, source: AbstractEventSource, parent: QWidget | None):
        super().__init__(parent)
        self._source = source
        self.setWindowTitle("Export")
        self.page_intro = PageExportIntro()
        self.page_settings = PageExportSettings(source.get_settings())
        self.page_progress = PageExportProgress(source)
        self.addPage(self.page_intro)
        self.addPage(self.page_settings)
        self.addPage(self.page_progress)
        self.option_filename = None
        self.option_compressed = False
        self.option_encrypted = source.get_settings().is_e2e_encryption_enabled()

    def set_filename(self, filename):
        self.option_filename = filename

    def set_encrypted(self, encrypted):
        self.option_encrypted = encrypted

    def set_compressed(self, compressed):
        self.option_compressed = compressed


if __name__ == '__main__':
    app = QApplication([])
    src = FileEventSource[Tenant](QtSettings())
    src.start()
    wizard = ExportWizard(src, None)
    wizard.show()
    sys.exit(app.exec())

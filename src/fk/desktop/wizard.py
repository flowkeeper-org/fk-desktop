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

from PySide6.QtWidgets import QWizardPage, QLabel, QVBoxLayout, QApplication, QWizard, QCheckBox, QLineEdit

app = QApplication([])

intro_page = QWizardPage()
intro_page.setTitle("Data export")
label = QLabel("This wizard will help you export Flowkeeper data to file.")
label.setWordWrap(True)
layout = QVBoxLayout()
layout.addWidget(label)
intro_page.setLayout(layout)

settings_page = QWizardPage()
settings_page.setTitle("Settings")
layout = QVBoxLayout()
label = QLabel("Select data source")
label.setWordWrap(True)
layout.addWidget(label)
export_location = QLineEdit()
export_location.setPlaceholderText('Export filename')
layout.addWidget(export_location)
export_compress = QCheckBox('Compress data')
layout.addWidget(export_compress)
settings_page.setLayout(layout)

wizard = QWizard()
wizard.addPage(intro_page)
wizard.addPage(settings_page)
wizard.setWindowTitle("Export")
wizard.show()

sys.exit(app.exec())

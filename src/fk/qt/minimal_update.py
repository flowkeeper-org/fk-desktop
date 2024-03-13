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

from PySide6.QtWidgets import QTextEdit
from semantic_version import Version

from fk.qt.app_version import get_current_version, get_latest_version
from fk.qt.minimal_common import window, main_loop, app

txt = QTextEdit(window)


def update(latest: Version, changelog: str):
    txt.setMarkdown(f'Current version: {get_current_version()}\n\nLatest version: {latest}\n\nChangelog: \n\n{changelog}')


get_latest_version(app, update)
window.setCentralWidget(txt)

main_loop(start_source=False)

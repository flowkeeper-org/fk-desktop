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
import json
import logging
import re
from typing import Callable

from PySide6.QtCore import QFile, QObject
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from semantic_version import Version

logger = logging.getLogger(__name__)
CHANGELOG_REGEX = re.compile(r'### v(.+) \(.*')
GITHUB_TAG_REGEX = re.compile(r'v(.+)')
GITHUB_API_URL = 'https://api.flowkeeper.org/repos/flowkeeper-org/fk-desktop/releases/latest?source=desktop'


def get_current_version() -> Version:
    file = QFile(":/CHANGELOG.txt")
    file.open(QFile.OpenModeFlag.ReadOnly)
    first_line = file.readLine().toStdString()
    file.close()

    m = CHANGELOG_REGEX.search(first_line)
    if m is not None:
        return Version(m.group(1))

    raise Exception('Cannot extract the current Flowkeeper version from CHANGELOG.txt')


def _success(reply: QNetworkReply, callback: Callable[[Version, str], None]) -> None:
    s = reply.readAll().toStdString()
    try:
        j = json.loads(s)
    except Exception as err:
        logger.warning(f'Warning -- cannot parse GitHub response (invalid JSON): {s}', exc_info=err)
        callback(None, None)
        return
    if j is not None and 'name' in j:
        m = GITHUB_TAG_REGEX.search(j['name'])
        if m is None:
            raise Exception(f'Cannot extract the latest Flowkeeper version from GitHub tag name')
        else:
            callback(Version(m.group(1)), j['body'])


def _error(err: QNetworkReply.NetworkError, callback: Callable[[Version, str], None]) -> None:
    logger.warning(f'Warning -- cannot get the latest Flowkeeper version info from GitHub: {err}')
    callback(None, None)


def get_latest_version(parent: QObject, callback: Callable[[Version], None]) -> None:
    mgr = QNetworkAccessManager(parent)
    req = QNetworkRequest(GITHUB_API_URL)
    reply = mgr.get(req)
    reply.readyRead.connect(lambda: _success(reply, callback))
    reply.errorOccurred.connect(lambda err: _error(err, callback))

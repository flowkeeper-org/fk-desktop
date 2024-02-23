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
from pprint import pprint

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtNetworkAuth import QOAuth2AuthorizationCodeFlow, QOAuthHttpServerReplyHandler, QAbstractOAuth
from PySide6.QtWidgets import QPushButton

from fk.qt.minimal_common import window, main_loop


def mpf(stage, parameters):
    print('mpf:', stage, parameters)
    if stage == QAbstractOAuth.Stage.RequestingAccessToken:
        # parameters['code'] = [QByteArray.fromPercentEncoding(parameters['code'][0])]
        parameters['client_id'] = ['248052959881-pqd62jj04427c7amt7g72crmu591rip8.apps.googleusercontent.com']
        parameters['client_secret'] = ['...']
        parameters['code'] = [QUrl.fromPercentEncoding(parameters['code'][0])]
        parameters['redirect_uri'] = ['http://127.0.0.1:8888/']
    elif stage == QAbstractOAuth.Stage.RequestingAuthorization:
        parameters['access_type'] = ['offline']
        parameters['prompt'] = ['prompt']
    pprint(parameters)


def login():
    mgr = QNetworkAccessManager(window)
    reply_handler = QOAuthHttpServerReplyHandler(8888, window)

    flow = QOAuth2AuthorizationCodeFlow('248052959881-pqd62jj04427c7amt7g72crmu591rip8.apps.googleusercontent.com',
                                        'https://accounts.google.com/o/oauth2/auth',
                                        'http://localhost:8090/token',
                                        mgr,
                                        window)
    flow.setScope('email')
    flow.setClientIdentifierSharedKey('...')
    flow.authorizeWithBrowser.connect(QDesktopServices.openUrl)
    flow.setReplyHandler(reply_handler)
    flow.setModifyParametersFunction(mpf)
    flow.granted.connect(lambda t: print('Granted:', flow.token()))

    print('Logging in...')
    flow.grant()
    print('Grant requested')


button = QPushButton(window)
button.setText('Login...')
button.clicked.connect(login)
window.setCentralWidget(button)

main_loop()

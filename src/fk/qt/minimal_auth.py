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
import base64
import json

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtNetworkAuth import QOAuth2AuthorizationCodeFlow, QOAuthHttpServerReplyHandler, QAbstractOAuth
from PySide6.QtWidgets import QPushButton

from fk.qt.minimal_common import window, main_loop

client_id = '248052959881-pqd62jj04427c7amt7g72crmu591rip8.apps.googleusercontent.com'
client_secret = '...'
local_port = 18889
auth_url = 'https://accounts.google.com/o/oauth2/auth'
token_url = 'https://oauth2.googleapis.com/token'


def fix_parameters(stage, parameters):
    if stage == QAbstractOAuth.Stage.RequestingAccessToken:
        parameters['client_id'] = [client_id]
        parameters['client_secret'] = [client_secret]
        parameters['code'] = [QUrl.fromPercentEncoding(parameters['code'][0])]
        parameters['redirect_uri'] = [f'http://127.0.0.1:{local_port}/']
    elif stage == QAbstractOAuth.Stage.RequestingAuthorization:
        parameters['access_type'] = ['offline']
    return parameters


def login():
    mgr = QNetworkAccessManager(window)
    flow = QOAuth2AuthorizationCodeFlow(client_id, auth_url, token_url, mgr, window)
    flow.setScope('email')
    flow.setClientIdentifierSharedKey(client_secret)
    flow.authorizeWithBrowser.connect(QDesktopServices.openUrl)
    flow.setReplyHandler(QOAuthHttpServerReplyHandler(local_port, window))
    flow.setModifyParametersFunction(fix_parameters)
    flow.granted.connect(lambda: pp(flow))
    flow.grant()


def refresh():
    mgr = QNetworkAccessManager(window)
    flow = QOAuth2AuthorizationCodeFlow(client_id, auth_url, token_url, mgr, window)
    flow.setScope('email')
    flow.setClientIdentifierSharedKey(client_secret)
    flow.setRefreshToken('1//03NqJ3kgUh3GACgYIARAAGAMSNwF-L9Ir7UR7re7_ZqmK5ZgSIr5JcNpu7V6_t9pv3iKI1TBfI_z9_sPgjvJnvZHPljKqLL0XHMk')
    flow.authorizeWithBrowser.connect(QDesktopServices.openUrl)
    flow.setReplyHandler(QOAuthHttpServerReplyHandler(local_port, window))
    flow.setModifyParametersFunction(fix_parameters)
    flow.granted.connect(lambda: pp(flow))
    flow.refreshAccessToken()


def pp(flow: QOAuth2AuthorizationCodeFlow):
    print('Access token:', flow.token())
    id_token = flow.extraTokens().get('id_token', None)
    print('ID token:', id_token)
    b = bytes(id_token.split('.')[1], 'iso8859-1')
    t = json.loads(base64.decodebytes(b + b'===='))
    email = t['email']
    print('Email:', email)
    print('Refresh token:', flow.refreshToken())


button = QPushButton(window)
button.setText('Login...')
button.clicked.connect(refresh)
window.setCentralWidget(button)

main_loop()

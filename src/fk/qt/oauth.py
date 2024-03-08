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

from typing import Callable

from PySide6.QtCore import QUrl, QObject
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtNetworkAuth import QAbstractOAuth, QOAuth2AuthorizationCodeFlow, QOAuthHttpServerReplyHandler

client_id = '248052959881-pqd62jj04427c7amt7g72crmu591rip8.apps.googleusercontent.com'
client_secret = '...'
local_port = 8888
auth_url = 'https://accounts.google.com/o/oauth2/auth'
token_url = 'https://oauth2.googleapis.com/token'


class AuthenticationRecord:
    email: str
    refresh_token: str
    access_token: str
    id_token: str


def _fix_parameters(stage, parameters):
    if stage == QAbstractOAuth.Stage.RequestingAccessToken:
        parameters['client_id'] = [client_id]
        parameters['client_secret'] = [client_secret]
        parameters['code'] = [QUrl.fromPercentEncoding(parameters['code'][0])]
        parameters['redirect_uri'] = [f'http://127.0.0.1:{local_port}/']
    elif stage == QAbstractOAuth.Stage.RequestingAuthorization:
        parameters['access_type'] = ['offline']
    return parameters


def authenticate(parent: QObject, callback: Callable[[AuthenticationRecord], None]):
    mgr = QNetworkAccessManager(parent)
    flow = QOAuth2AuthorizationCodeFlow(client_id, auth_url, token_url, mgr, parent)
    flow.setScope('email')
    flow.setClientIdentifierSharedKey(client_secret)
    flow.authorizeWithBrowser.connect(QDesktopServices.openUrl)
    flow.setReplyHandler(QOAuthHttpServerReplyHandler(local_port, parent))
    flow.setModifyParametersFunction(_fix_parameters)
    flow.granted.connect(lambda: _granted(flow, callback))
    flow.grant()


def _granted(flow: QOAuth2AuthorizationCodeFlow, callback: Callable[[AuthenticationRecord], None]):
    id_token = flow.extraTokens().get('id_token', None)
    print('OAuth access granted:')
    print(' - Access token:', flow.token())
    print(' - ID token:', id_token)
    print(' - Refresh token:', flow.refreshToken())
    auth = AuthenticationRecord()
    auth.email = '???'
    auth.access_token = flow.token()
    auth.id_token = id_token
    auth.refresh_token = flow.refreshToken()
    callback(auth)


def get_id_token(refresh_token: str) -> str:
    # TODO: Get access token from this refresh one, then get ID token
    return '123'

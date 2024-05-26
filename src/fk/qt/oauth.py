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
import logging
from typing import Callable

from PySide6.QtCore import QUrl, QObject
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtNetworkAuth import QAbstractOAuth, QOAuth2AuthorizationCodeFlow, QOAuthHttpServerReplyHandler

logger = logging.getLogger(__name__)

client_id = '248052959881-pqd62jj04427c7amt7g72crmu591rip8.apps.googleusercontent.com'
local_port = 64166
auth_url = 'https://accounts.google.com/o/oauth2/auth'
token_url = 'https://app.flowkeeper.org/token'

MGR: QNetworkAccessManager = None
HANDLER: QOAuthHttpServerReplyHandler = None


class AuthenticationRecord:
    type: str
    email: str
    refresh_token: str
    access_token: str
    id_token: str

    def __str__(self):
        return (f'AuthenticationRecord({self.type}):\n'
                f' - Email: {self.email}\n'
                f' - Refresh token: {self.refresh_token}\n'
                f' - Access token: {self.access_token}\n'
                f' - ID token: {self.id_token}')


def _fix_parameters(stage, parameters):
    if stage == QAbstractOAuth.Stage.RequestingAccessToken:
        parameters['client_id'] = [client_id]
        # The client secret is handled on the server side
        # parameters['client_secret'] = [client_secret]
        parameters['code'] = [QUrl.fromPercentEncoding(parameters['code'][0])]
        parameters['redirect_uri'] = [f'http://127.0.0.1:{local_port}/']
    elif stage == QAbstractOAuth.Stage.RequestingAuthorization:
        parameters['access_type'] = ['offline']
    return parameters


def authenticate(parent: QObject, callback: Callable[[AuthenticationRecord], None]) -> None:
    logger.debug(f'Authenticating for a refresh token')
    return _perform_flow(parent, callback, None)


def get_id_token(parent: QObject, callback: Callable[[AuthenticationRecord], None], refresh_token: str) -> None:
    logger.debug(f'Getting ID token for refresh token {refresh_token}')
    _perform_flow(parent, callback, refresh_token)


def _perform_flow(parent: QObject, callback: Callable[[AuthenticationRecord], None], refresh_token: str | None):
    global MGR, HANDLER
    if MGR is None:
        MGR = QNetworkAccessManager(parent)
    if HANDLER is None:
        HANDLER = QOAuthHttpServerReplyHandler(local_port, parent)
    flow = QOAuth2AuthorizationCodeFlow(client_id, auth_url, token_url, MGR, parent)
    flow.setScope('email')
    if refresh_token is not None:
        flow.setRefreshToken(refresh_token)
    # We are adding the client secret on the server side
    # flow.setClientIdentifierSharedKey(client_secret)
    flow.authorizeWithBrowser.connect(QDesktopServices.openUrl)
    flow.setReplyHandler(HANDLER)
    flow.setModifyParametersFunction(_fix_parameters)
    flow.granted.connect(lambda: _granted(flow, callback))
    flow.error.connect(lambda err: _error(err, flow, callback))
    if refresh_token is not None:
        logger.debug('Refreshing access token')
        flow.refreshAccessToken()
    else:
        logger.debug('Requesting access grant')
        flow.grant()


def _extract_email(id_token: str) -> str:
    b = bytes(id_token.split('.')[1], 'iso8859-1')
    t = json.loads(base64.decodebytes(b + b'===='))
    logger.debug(f'Extracted JWT info: {json.dumps(t)}')
    return t['email']


def _error(err, flow: QOAuth2AuthorizationCodeFlow, callback: Callable[[AuthenticationRecord], None]):
    logger.error('Error in OAuth2 Authorization Flow', exc_info=err)


def _granted(flow: QOAuth2AuthorizationCodeFlow, callback: Callable[[AuthenticationRecord], None]):
    logger.debug('Access granted')
    id_token = flow.extraTokens().get('id_token', None)
    email = _extract_email(id_token)
    auth = AuthenticationRecord()
    auth.email = email
    auth.type = 'google'
    auth.access_token = flow.token()
    auth.id_token = id_token
    auth.refresh_token = flow.refreshToken()
    logger.debug(f'OAuth access granted / refreshed: {auth}')
    callback(auth)

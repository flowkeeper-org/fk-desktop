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
import webbrowser
from typing import Callable
from urllib.request import urlopen

from PySide6.QtCore import QUrl, QObject, QBuffer, QIODevice, QByteArray
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager
from PySide6.QtNetworkAuth import QAbstractOAuth, QOAuth2AuthorizationCodeFlow, QOAuthHttpServerReplyHandler

logger = logging.getLogger(__name__)

client_id = 'flowkeeper-desktop'
local_port = 64166
auth_url = 'http://localhost:8080/realms/flowkeeper/protocol/openid-connect/auth'
token_url = 'http://localhost:8080/realms/flowkeeper/protocol/openid-connect/token'
scopes = 'email profile openid'

MGR: QNetworkAccessManager = None
HANDLER: QOAuthHttpServerReplyHandler = None


class AuthenticationRecord:
    type: str
    email: str
    picture: str
    fullname: str
    refresh_token: str
    access_token: str
    id_token: str

    def __str__(self):
        return (f'AuthenticationRecord({self.type}):\n'
                f' - Email: {self.email}\n'
                f' - Profile picture: {self.picture}\n'
                f' - Full name: {self.fullname}\n'
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
        parameters['prompt'] = ['consent']
    return parameters


def authenticate(parent: QObject, callback: Callable[[AuthenticationRecord], None]) -> None:
    logger.debug(f'Authenticating for a refresh token')
    return _perform_flow(parent, callback, None)


def get_id_token(parent: QObject, callback: Callable[[AuthenticationRecord], None], refresh_token: str) -> None:
    logger.debug(f'Getting ID token for refresh token {refresh_token}')
    _perform_flow(parent, callback, refresh_token)


def open_url(url: QUrl | str) -> None:
    if isinstance(url, QUrl):
        webbrowser.open(url.toString(), 2)
    else:
        webbrowser.open(url, 2)


def _perform_flow(parent: QObject, callback: Callable[[AuthenticationRecord], None], refresh_token: str | None):
    global MGR, HANDLER
    if MGR is None:
        MGR = QNetworkAccessManager(parent)
    if HANDLER is None:
        HANDLER = QOAuthHttpServerReplyHandler(local_port, parent)
    flow = QOAuth2AuthorizationCodeFlow(client_id, auth_url, token_url, MGR, parent)
    flow.setScope(scopes)
    if refresh_token is not None:
        flow.setRefreshToken(refresh_token)
    # We are adding the client secret on the server side
    # flow.setClientIdentifierSharedKey(client_secret)
    flow.authorizeWithBrowser.connect(open_url)
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


def _picture_to_base64(url: str):
    if url:
        logger.debug(f'Loading user profile picture from {url}')
        data = urlopen(url).read()
        logger.debug(f'Resizing picture to 32x32')
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        image = pixmap.scaled(32, 32).toImage()
        logger.debug(f'Extracting image as base64')
        output = QByteArray()
        buffer = QBuffer(output)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        return output.toBase64().toStdString()
    else:
        return ''


def _extract_user_info(id_token: str) -> (str, str):
    b = bytes(id_token.split('.')[1], 'iso8859-1')
    t = json.loads(base64.decodebytes(b + b'===='))
    logger.debug(f'Extracted JWT info: {t.keys()}')
    return t['email'], _picture_to_base64(t.get('picture', '')), t.get('name', '')


def _error(err, flow: QOAuth2AuthorizationCodeFlow, callback: Callable[[AuthenticationRecord], None]):
    logger.error('Error in OAuth2 Authorization Flow', exc_info=err)


def _granted(flow: QOAuth2AuthorizationCodeFlow, callback: Callable[[AuthenticationRecord], None]):
    logger.debug(f'Access granted. Extra tokens: {flow.extraTokens().keys()}')
    id_token = flow.extraTokens().get('id_token', None)
    auth = AuthenticationRecord()
    auth.email, auth.picture, auth.fullname = _extract_user_info(id_token)
    auth.type = 'oauth'
    auth.access_token = flow.token()
    auth.id_token = id_token
    auth.refresh_token = flow.refreshToken()
    logger.debug(f'OAuth access granted / refreshed: {auth}')
    callback(auth)

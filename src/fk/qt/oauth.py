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


class AuthenticationRecord:
    email: str
    refresh_token: str
    access_token: str
    id_token: str


def authenticate(callback: Callable[[AuthenticationRecord], None]):
    auth = AuthenticationRecord()
    auth.email = '123'
    callback(auth)


def get_id_token(refresh_token: str) -> str:
    # TODO: Get access token from this refresh one, then get ID token
    return '123'

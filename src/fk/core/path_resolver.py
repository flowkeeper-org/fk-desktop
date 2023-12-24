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

from os import path

ROOT_DIR: str | None = None


# TODO: This is not used anymore, as we switched to Qt Resources fwk
# Consider removing
def resolve_path(filename: str) -> str:
    global ROOT_DIR
    if ROOT_DIR is None:
        ROOT_DIR = path.dirname(__file__)
        if '_MEI' in ROOT_DIR:
            ROOT_DIR = path.abspath(path.join(path.join(path.dirname(__file__), ".."), ".."))
            print(f'Running bundled, root dir is {ROOT_DIR}')
        else:
            ROOT_DIR = path.abspath(path.join(path.join(path.join(path.dirname(__file__), ".."), ".."), ".."))
            print(f'Running unbundled, root dir is {ROOT_DIR}')
    return path.abspath(path.join(ROOT_DIR, filename))

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
import os
import platform


def get_sandbox_type() -> str | None:
    # See https://stackoverflow.com/questions/75274925/is-there-a-way-to-find-out-if-i-am-running-inside-a-flatpak-appimage-or-another
    if platform.system() == 'Linux':
        if os.environ.get('container') is not None:
            return 'Flatpak'
        elif os.environ.get('SNAP') is not None:
            return 'Snap'
        elif os.environ.get('APPIMAGE') is not None:
            return 'AppImage'
    return None

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
import datetime

from fk.core.abstract_data_item import generate_unique_name
from fk.core.abstract_event_source import AbstractEventSource


def generate_backlog_name(source: AbstractEventSource) -> str:
    prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')  # Locale-formatted
    return generate_unique_name(prefix, source.get_data().get_current_user().names())

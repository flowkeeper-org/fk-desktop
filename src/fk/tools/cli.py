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
from argparse import ArgumentParser, Namespace
from typing import Type, Callable

from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog_strategies import CreateBacklogStrategy, DeleteBacklogStrategy
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.no_cryptograph import NoCryptograph
from fk.core.tenant import Tenant
from fk.core.user import User

logger = logging.getLogger(__name__)


def strategy(cls: Type[AbstractStrategy],
             params: list[str],
             display: Callable[[Tenant], None]) -> Callable[[AbstractEventSource[Tenant]], None]:
    def callback(source: AbstractEventSource[Tenant]):
        source.execute(cls, params)
        display(source.get_data())
    return callback

def dump(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))

def list_backlogs(source: AbstractEventSource[Tenant], uid: str | None, name_pattern: str | None) -> None:
    user: User = source.get_data().get_current_user()
    if uid is not None:
        dump(user[uid].to_dict())
    else:
        if name_pattern is not None:
            regex = re.compile(name_pattern)
            found = list()
            for b in user.values():
                if regex.match(b.get_name()):
                    found.append(b.to_dict())
            dump(found)
        else:
            dump([b.to_dict() for b in user.values()])

def execute(callback: Callable[[AbstractEventSource[Tenant]], None]) -> None:
    settings = MockSettings(filename=filename)
    source = FileEventSource[Tenant](settings,
                                     NoCryptograph(settings),
                                     Tenant(settings))
    source.start()  # FileEventSource uses synchronous IO
    callback(source)

def default(args) -> None:
    parser.print_help()

def backlog(args) -> None:
    global filename
    filename = args.file
    if args.add:
        uid = generate_uid()
        execute(strategy(CreateBacklogStrategy,
                         [uid, args.add],
                         lambda tenant: dump(tenant.get_current_user()[uid].to_dict())))
    elif args.delete:
        execute(strategy(DeleteBacklogStrategy,
                         [args.delete],
                         lambda tenant: print('{}')))
    elif args.list:
        execute(lambda source: list_backlogs(source, None, None))
    elif args.get:
        execute(lambda source: list_backlogs(source, args.get, None))
    elif args.find:
        execute(lambda source: list_backlogs(source, None, args.find))
    else:
        backlog_parser.print_help()


if __name__ == '__main__':
    parser = ArgumentParser(description="Flowkeeper command-line client")
    parser.set_defaults(func=default)

    subparsers = parser.add_subparsers(title='Available commands')

    backlog_parser = subparsers.add_parser('backlog', help='backlog help')
    backlog_parser.add_argument("--add", help="Add backlog")
    backlog_parser.add_argument("--delete", help="Delete backlog by UID")
    backlog_parser.add_argument("--get", help="Describe backlog by UID")
    backlog_parser.add_argument("--list", help="List all backlogs", action='store_true')
    backlog_parser.add_argument("--find", help="Find backlog by applying this regex to its name")
    backlog_parser.add_argument("--file", required=True, help="Data file")
    backlog_parser.set_defaults(func=backlog)

    parser.add_argument("--debug", action='store_true', help="Debug output for troubleshooting Flowkeeper")

    args: Namespace = parser.parse_args()

    filename = None
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    args.func(args)

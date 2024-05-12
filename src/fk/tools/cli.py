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

import sys
import uuid

from fk.core import events
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.events import SourceMessagesProcessed
from fk.core.file_event_source import FileEventSource
from fk.core.mock_settings import MockSettings
from fk.core.tenant import Tenant
from fk.qt.websocket_event_source import WebsocketEventSource


def generate_uid():
    return str(uuid.uuid4())


def log(event, **kwargs):
    print(f'> {event}:')
    for arg in kwargs:
        print(f'  {arg}: {kwargs[arg]}')
    print()


def view(source: AbstractEventSource):
    source.on('*', log)
    source.on(events.SourceMessagesProcessed, lambda event: do_view(source))

    print('*** Replay events ***')
    source.start()


def do_view(source: AbstractEventSource):
    print()
    print('*** Strategies ***')
    print(source)

    print()
    print('*** Data store ***')
    for user in source.get_data().values():
        print(f"{user}")
        for backlog in user.values():
            print(f" - {backlog}")
            for workitem in backlog.values():
                print(f"   - {workitem}")


def repair(source: FileEventSource):
    print('*** Repairing ***')
    source.repair()
    print('*** Done, check -repaired file ***')


def esc(st):
    return st.replace('\\', '\\\\').replace('"', '\\"')


def export_v2(source):
    print('*** Exporting for V2 ***')
    source.on(SourceMessagesProcessed, lambda: do_export_v2(source))
    source.start()


def do_export_v2(source: AbstractEventSource):
    print('*** Exporting for V2 ***')

    seq = 1
    when = '2023-01-01 00:00:01+00:00'

    with open('export-v2.txt', 'w', encoding='UTF-8') as f:
        for user in source.get_data().values():
            if user.get_identity() == 'admin@local.host':
                continue
            f.write(f'{seq}, {when}, admin@local.host: '
                    f'CreateUser("{esc(user.get_identity())}", "{esc(user.get_name())}")\n')
            seq += 1

        # 1 - Create everything
        for backlog in source.backlogs():
            backlog._uid = generate_uid()
            f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                    f'CreateBacklog("{backlog.get_uid()}", "{esc(backlog.get_name())}")\n')
            seq += 1
            for workitem in backlog.values():
                workitem._uid = generate_uid()
                f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                        f'CreateWorkitem("{workitem.get_uid()}", "{backlog.get_uid()}", '
                        f'"{esc(workitem.get_name())}")\n')
                seq += 1
                if len(workitem) > 0:
                    f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                            f'AddPomodoro("{workitem.get_uid()}", "{len(workitem)}")\n')
                    seq += 1

        # 2 - Update pomodoro states
        for backlog in source.backlogs():
            for workitem in backlog.values():
                for pomodoro in workitem.values():
                    if pomodoro.is_canceled() or pomodoro.is_finished():
                        f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                                f'StartWork("{workitem.get_uid()}", "1500")\n')
                        seq += 1
                        f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                                f'StartRest("{workitem.get_uid()}", "300")\n')
                        seq += 1
                        f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                                f'CompletePomodoro("{workitem.get_uid()}", "{esc(pomodoro.get_state())}")\n')
                        seq += 1

        # 3 - Seal workitems
        for backlog in source.backlogs():
            for workitem in backlog.values():
                if workitem.is_sealed():
                    f.write(f'{seq}, {when}, {backlog.get_owner().get_identity()}: '
                            f'CompleteWorkitem("{workitem.get_uid()}", "finished")\n')
                    seq += 1

    print('*** Done, check export-v2.txt file ***')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) == 2 else 'view'

    #s = FileEventSource(MockSettings(), None)
    s = WebsocketEventSource[Tenant](MockSettings(filename='/home/w/flowkeeper-data-new.txt'), None, None)

    if mode == 'view':
        view(s)
    elif mode == 'repair':
        repair(s)
    elif mode == 'export-v2':
        export_v2(s)

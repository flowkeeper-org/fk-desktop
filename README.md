# Flowkeeper Desktop

This README is work in progress.

## Building

Flowkeeper has a single dependency -- Qt 6.6, which in turn requires Python 3.11. If you want to
build it with Ubuntu 20.04 or Debian 11, both of which come with older versions of Python, you
would have to [compile Python 3.11 first](https://fostips.com/install-python-3-10-debian-11/).

Install dependencies:

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The Websocket backend relies on Qt WebSockets module, which in turn
requires OpenSSL 3.0. Note that some of the legacy OS like Ubuntu 20.04 require 
manual steps to install OpenSSL v3.

From here you can start coding. If you make any changes to resources
(files in `/res` directory) you need to rebuild the corresponding Python
classes:

```shell
./generate-resource.sh
```

Finally, to run Flowkeeper:

```shell
PYTHONPATH=src python -m fk.desktop.desktop
```

To run unit tests w/test coverage:

```shell
PYTHONPATH=src python -m coverage run -m unittest discover -v fk.tests
python -m coverage html
```

To build an installer for your platform (the standalone binary is placed in `dist/desktop`):

```shell
pyinstaller desktop.spec
```

## Technical details

### Data structue

- Tenant: AbstractDataContainer
  - User: AbstractDataContainer
    - Backlog: AbstractDataContainer
      - Workitem: AbstractDataContainer
        - Pomodoro: AbstractDataItem

### Events

Whenever anything changes in the underlying data model, Flowkeeper emits events. To emit an event, the class needs
to subclass `AbstractEventSource`. All UI updates should be based on those events.

- AbstractEventSource
  - `BeforeUserCreate(user_identity: str, user_name: str)`, `AfterUserCreate(user: User)`
  - `BeforeUserDelete(user: User)`, `AfterUserDelete(--//--)`
  - `BeforeUserRename(user: User, old_name: str, new_name: str)`, `AfterUserRename(--//--)`
  - `BeforeBacklogCreate(backlog_name: str, backlog_owner: User, backlog_uid: str)`, `AfterBacklogCreate(backlog: Backlog)`
  - `BeforeBacklogDelete(backlog: Backlog)`, `AfterBacklogDelete(--//--)`
  - `BeforeBacklogRename(backlog: Backlog, old_name: str, new_name: str)`, `AfterBacklogRename(--//--)`
  - `BeforeWorkitemCreate(backlog_uid: str, workitem_uid: str, workitem_name: str)`, `AfterWorkitemCreate(workitem: Workitem)`
  - `BeforeWorkitemComplete(workitem: Workitem, target_state: str)`, `AfterWorkitemComplete(--//--)`
  - `BeforeWorkitemStart(pomodoro: Pomodoro, workitem: Workitem, work_duration: int)`, `AfterWorkitemStart(--//--)`
  - `BeforeWorkitemDelete(workitem: Workitem)`, `AfterWorkitemDelete(--//--)`
  - `BeforeWorkitemRename(workitem: Workitem, old_name: str, new_name: str)`, `AfterWorkitemRename(--//--)`
  - `BeforePomodoroAdd(workitem: Workitem, num_pomodoros: int)`, `AfterPomodoroAdd(--//--)`
  - `BeforePomodoroRemove(workitem: Workitem, num_pomodoros: int, pomodoros: List<Pomodoro>)`, `AfterPomodoroRemove(--//--)`
  - `BeforePomodoroWorkStart(pomodoro: Pomodoro, workitem: Workitem, work_duration: int)`, `AfterPomodoroWorkStart(--//--)`
  - `BeforePomodoroRestStart(pomodoro: Pomodoro, workitem: Workitem, rest_duration: int)`, `AfterPomodoroRestStart(--//--)`
  - `BeforePomodoroComplete(pomodoro: Pomodoro, workitem: Workitem, target_state: str)`, `AfterPomodoroComplete`
  - `SourceMessagesRequested()`, `SourceMessagesProcessed()`
  - `BeforeMessageProcessed(strategy: AbstractStrategy, auto: Bool)`, `AfterMessageProcessed(--//--)`
  - `PongReceived(uid: str)`

- AbstractSettings
  - `BeforeSettingChanged(name: str, old_value: str, new_value: str)`, `AfterSettingChanged(--//--)`

- AbstractTableView
  - `BeforeSelectionChanged(before: AbstractDataItem, after: AbstractDataItem)`, `AfterSelectionChanged(--//--)`

- Application
  - `AfterFontsChanged(main_font: QFont, header_font: QFont, application: Application)`
  - `AfterSourceChanged(source: AbstractEventSource)`

- Heartbeat
  - `WentOnline(ping: int)`, `WentOffline(after: int, last_received: datetime)`

- PomodoroTimer
  - `TimerTick(timer: PomodoroTimer)`
  - `TimerWorkStart(timer: PomodoroTimer)`
  - `TimerWorkComplete(timer: PomodoroTimer)`
  - `TimerRestComplete(timer: PomodoroTimer, pomodoro: Pomodoro, workitem: Workitem)`

The listeners can also pass the `carry` parameter -- TODO: Explain it. The mandatory `event` parameter for the callbacks 
contains the event name.

### Commands

You may find those as _Strategies_ in the code. They correspond to the end-user actions /
data mutations. Each command takes two or three parameters.

- `CreateBacklog("<BACKLOG_NAME>", "")` - Creates new backlog.
- `CreateWorkitem("<WORKITEM_NAME>", "<FLAGS>", "<INITIAL_POMODOROS>")`
- `AddToBacklog("<BACKLOG_NAME>", "<WORKITEM_NAME>")`
- `RemoveFromBacklog("<BACKLOG_NAME>", "<WORKITEM_NAME>")` - Removes workitem from backlog.
It remains in the Global backlog.
- `DeleteBacklog("<BACKLOG_NAME>", "")`
- `DeleteWorkitem("<WORKITEM_NAME>", "")` - It will delete
- `StartWork("<WORKITEM_NAME>", "")` - It will fail if there's no more Pomodoros left.
- `CompletePomodoro("<WORKITEM_NAME>", "<POMODORO_STATE>")`
- `CompleteWorkitem("<WORKITEM_NAME>", "<WORKITEM_STATE>")`

Apart from "business data", each command has a few metadata field, associated with it:
- Timestamp
- Username (who executed it)

### Design considerations

The core is designed with the following assumptions:

1. All messages are sent by clients. The server doesn't add any messages of its own, even
though it could have its own timers. This is done to simplify servers, and enable "dumb"
backends like plain files.
2. A client might be shut down at any moment. Most importantly, there can be zero clients 
running in the middle of a Pomodoro.
3. Two clients must synchronize their changes in real time, meaning that they can't make
conflicting changes offline. This is achieved via message sequencing.
4. Some messages might be missing from the end of the list (e.g. the client is offline and
they haven't arrived yet), but we can't have gaps in the middle of the history. It means
that the history must always be consistent. If we detect an inconsistency in the hisory
(e.g. 5 minutes of rest start on a pomodoro in "new" state, i.e. we missed the "work" state
completely), such inconsistencies result in the parsing failure, crashing the client.
We don't try to "fix" the history by adding records retroactively. 
5. The history is immutable, but we can create a new one, which is a compressed version
of the original, as long as it results in the exact same final state of the data model.
6. If a user tries to delete or complete a workitem in the middle of its own pomodoro, the
core will void this pomodoro, emitting correct events.
7. The history preserves all data, so we don't have to be too careful about deleting things.
If a backlog, workitem or user is deleted -- the object simply gets deleted. We don't use
"is_deleted" flags, and we don't move things to "orphaned" storage. If we need to restore
a deleted object -- we'll find a way how to do it by processing the history.
8. Strategies are only executed as a result of users' actions or timer events. Client
startup or shutdown won't add any strategies to the history.
9. The Timer never fires "in the past".

## Copyright

Copyright (c) 2023 Constantine Kulak.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

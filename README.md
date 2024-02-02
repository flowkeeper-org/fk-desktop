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

Flowkeeper data model is strictly hierarchical:

- Tenant: AbstractDataContainer
  - User: AbstractDataContainer
    - Backlog: AbstractDataContainer
      - Workitem: AbstractDataContainer
        - Pomodoro: AbstractDataItem

`AbstractDataContainer` acts as a `dict<uid, T>`, and `AbstractDataItem` represents a domain object with 
`uid`, `parent`, `create_date` and `last_modified_date`. 

Due to its tree nature, sharing backlogs and workitems should be implemented via symlinks.

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

All data objects are keyed with `UID`, which is an arbitrary string, typically a GUID.

Apart from "business data", each command has a few metadata fields, associated with it:
- Sequence number, used for ordering and checking uniqueness
- Execution timestamp
- Execution user

#### User strategies

Note that users have emails as IDs.

- `CreateUser("<EMAIL>", "<USER_NAME>")` - Fails if a user with this email already 
exists, or a non-System user tries to execute this strategy. Emits `BeforeUserCreate` / 
`AfterUserCreate` events.
- `DeleteUser("<EMAIL>", "")` - Deletes a user **recursively**, i.e. executes
`DeleteBacklogStrategy` for each of the child backlogs. Fails if a user with a given 
email is not found, if a non-System user tries to execute this strategy, or if we are
trying to delete a System user. Emits `BeforeUserDelete` / `AfterUserDelete` events.
- `RenameUser("<EMAIL>", "<NEW_NAME>")` - Fails if a user with a given email is not found,
if a non-System user tries to execute this strategy, or if we are trying to rename a System 
user. Emits `BeforeUserRename` / `AfterUserRename` events.

#### Backlog strategies

- `CreateBacklog("<UID>", "<BACKLOG_NAME>")` - Fails if a backlog with this UID already 
exists for the calling user. Emits `BeforeBacklogCreate` / `AfterBacklogCreate` events.
- `DeleteBacklog("<UID>", "")` - Deletes a backlog **recursively**, i.e. executes
`DeleteWorkitemStrategy` for each of the child workitems. Fails if a backlog with a given 
UID is not found for the calling user. Emits `BeforeBacklogDelete` / `AfterBacklogDelete` 
events.
- `RenameBacklog("<UID>", "<NEW_NAME>")` - Fails if a backlog with a given UID is not found 
for the calling user. Emits `BeforeBacklogRename` / `AfterBacklogRename` events.

#### Workitem strategies

- `CreateWorkitem("<WORKITEM_UID>", "<BACKLOG_UID>", "<WORKITEM_NAME>")` - Fails if a backlog 
with this UID is not found or if a workitem with this UID already exists in that backlog. 
Emits `BeforeWorkitemCreate` / `AfterWorkitemCreate` events.
- `DeleteWorkitem("<UID>", "")` - Deletes a workitem **recursively**, i.e. executes
`CompletePomodoroStrategy` with `canceled` state for each of the running pomodoros first. Fails 
if a workitem with a given UID is not found in any backlog. Emits `BeforeWorkitemDelete` / 
`AfterWorkitemDelete` events.
- `RenameWorkitem("<UID>", "<NEW_NAME>")` - Fails if a workitem with a given UID is not found in
any backlog or if it is sealed (finished or canceled). Doesn't do anything if the new name is 
identical to the old one, otherwise emits `BeforeWorkitemRename` / `AfterWorkitemRename` events.
- `CompleteWorkitem("<UID>", "<STATE>")` - Seals the workitem with a given state (`finished` or 
`canceled`) **recursively**, i.e. executes `CompletePomodoroStrategy` with `canceled` state for 
each of the running pomodoros, if any. Fails if a workitem with a given UID is not found in any 
backlog, if the target state is neither `finished` nor `canceled`, or if the workitem is already 
sealed. Emits `BeforeWorkitemComplete` / `AfterWorkitemComplete` events.

#### Pomodoro strategies

Individual pomodoros don't have their own UIDs for simplicity. Although UIDs exist in runtime,
they are generated on the fly and not persisted.

- `AddPomodoroStrategy("<WORKITEM_UID>", "<ADDED_COUNT>")` - Fails if the number of added 
pomodoros is less than 1, or if the workitem with specified UID is not found or sealed. Emits 
`BeforePomodoroAdd` / `AfterPomodoroAdd` events.
- `RemovePomodoroStrategy("<WORKITEM_UID>", "<REMOVED_COUNT>")` - Fails if the number of removed 
pomodoros is less than 1, or if the workitem with specified UID is not found or sealed, or if 
there's not enough startable (`new` state) pomodoros in the workitem. Emits 
`BeforePomodoroRemove` / `AfterPomodoroRemove` events.
- `CompletePomodoroStrategy("<WORKITEM_UID>", "<TARGET_STATE>")` - Fails if the workitem with 
specified UID is not found or sealed, or has no running pomodoros, or if the target state is
neither `finished` nor `canceled`. Emits `BeforePomodoroComplete` / `AfterPomodoroComplete` 
events.
- `StartWorkStrategy("<WORKITEM_UID>", "<WORK_DURATION_IN_SECONDS>")` - Fails if the workitem 
with specified UID is not found or sealed, or has no startable (`new`) pomodoros. If the 
specified work duration is `0`, then the default value at the pomodoro creation moment is used. 
If a Workitem is not yet running, it switches into `running` state, emitting a pair of 
`BeforeWorkitemStart` / `AfterWorkitemStart` events. As long as it doesn't fail, this strategy 
emits `BeforePomodoroWorkStart` / `AfterPomodoroWorkStart` events.
- `StartRestStrategy("<WORKITEM_UID>", "<REST_DURATION_IN_SECONDS>")` - Fails if the workitem 
with specified UID is not found or is not running, or has no in-work (`work` state) pomodoros. 
If the specified rest duration is `0`, then the default value at the pomodoro creation moment 
is used. Emits `BeforePomodoroRestStart` / `AfterPomodoroRestStart` events.

#### Server strategies

All below strategies are used with server-based event sources only, and are not persisted.

- `Authenticate("<EMAIL>", "<TOKEN>")` - This must be the first strategy sent by the client to 
the server, otherwise the latter closes the communication channel. Note that it doesn't specify 
token's format, leaving it to the authentication implementation.
- `Replay("<AFTER_SEQUENCE>")` - Used for requesting the replay of the strategies from the
server, starting from, but not including, `#AFTER_SEQUENCE`. The server may respond with one
or more messages with event history. 
- `ReplayCompleted()` - Not a true strategy (TODO -- Fix it), used by the server to signal the
last strategy in the replayed list.
- `Error("<ERROR_CODE>", "<ERROR_MESSAGE>")` - Sent by the server to report an error, e.g. wrong
credentials passed to `Authenticate` strategy. Flowkeeper Desktop raises a UI exception when
executing this strategy. This results in a message popup and a request to file a bug in GitHub.
- `PingStrategy("<UID>", "")` - The client sends this to verify connection to the server. It
expects to receive a `PongStrategy` response with the matching UID immediately after. If the
client doesn't receive a pong in a timely matter, it should switch to Offline / read-only mode.
- `PongStrategy("<UID>", "")` - Sent by the server as a reply to `PingStrategy`. If an Offline 
client receives a matching pong, it should switch back to Online mode.

#### Admin strategies

TODO: Server-only strategies for Pomodoro Server.

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

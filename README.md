# Flowkeeper Desktop

This README is work in progress.

## Data structue and ownership

- Backlog
- Workitem
- Pomodoro

## Backlogs

- Global: one per Owner
- Named: date + name

## Commands

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

## Design considerations

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

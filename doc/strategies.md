# Strategies

You may find those as _Strategies_ in the code. They correspond to the end-user actions /
data mutations. Each command takes two or three parameters.

All data objects are keyed with `UID`, which is an arbitrary string, typically a GUID.

Apart from "business data", each command has a few metadata fields, associated with it:
- Sequence number, used for ordering and checking uniqueness
- Execution timestamp
- Execution user

## User strategies

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

## Backlog strategies

- `CreateBacklog("<UID>", "<BACKLOG_NAME>")` - Fails if a backlog with this UID already 
exists for the calling user. Emits `BeforeBacklogCreate` / `AfterBacklogCreate` events.
- `DeleteBacklog("<UID>", "")` - Deletes a backlog **recursively**, i.e. executes
`DeleteWorkitemStrategy` for each of the child workitems. Fails if a backlog with a given 
UID is not found for the calling user. Emits `BeforeBacklogDelete` / `AfterBacklogDelete` 
events.
- `RenameBacklog("<UID>", "<NEW_NAME>")` - Fails if a backlog with a given UID is not found 
for the calling user. Emits `BeforeBacklogRename` / `AfterBacklogRename` events.

## Workitem strategies

- `CreateWorkitem("<WORKITEM_UID>", "<BACKLOG_UID>", "<WORKITEM_NAME>")` - Fails if a backlog 
with this UID is not found or if a workitem with this UID already exists in that backlog. 
Emits `BeforeWorkitemCreate` / `AfterWorkitemCreate` events.
- `DeleteWorkitem("<UID>", "")` - Deletes a workitem **recursively**, i.e. executes
`VoidPomodoroStrategy` for each of the running pomodoros first. Fails if a workitem with a given 
UID is not found in any backlog. Emits `BeforeWorkitemDelete` / `AfterWorkitemDelete` events.
- `RenameWorkitem("<UID>", "<NEW_NAME>")` - Fails if a workitem with a given UID is not found in
any backlog or if it is sealed (finished or canceled). Doesn't do anything if the new name is 
identical to the old one, otherwise emits `BeforeWorkitemRename` / `AfterWorkitemRename` events.
- `CompleteWorkitem("<UID>", "<STATE>")` - Seals the workitem with a given state (`finished` or 
`canceled`) **recursively**, i.e. executes `VoidPomodoroStrategy` for each of the running 
pomodoros, if any. Fails if a workitem with a given UID is not found in any backlog, if the 
target state is neither `finished` nor `canceled`, or if the workitem is already sealed. Emits 
`BeforeWorkitemComplete` / `AfterWorkitemComplete` events.

## Pomodoro strategies

Individual pomodoros don't have their own UIDs for simplicity. Although UIDs exist in runtime,
they are generated on the fly and not persisted.

- `AddPomodoroStrategy("<WORKITEM_UID>", "<ADDED_COUNT>")` - Fails if the number of added 
pomodoros is less than 1, or if the workitem with specified UID is not found or sealed. Emits 
`BeforePomodoroAdd` / `AfterPomodoroAdd` events.
- `RemovePomodoroStrategy("<WORKITEM_UID>", "<REMOVED_COUNT>")` - Fails if the number of removed 
pomodoros is less than 1, or if the workitem with specified UID is not found or sealed, or if 
there's not enough startable (`new` state) pomodoros in the workitem. Emits 
`BeforePomodoroRemove` / `AfterPomodoroRemove` events.
- `CompletePomodoroStrategy("<WORKITEM_UID>", "<TARGET_STATE>")` - **DEPRECATED** If the target
state is `canceled`, it works as a synonym for `VoidPomodoroStrategy`, otherwise it is ignored.
- `VoidPomodoroStrategy("<WORKITEM_UID>")` - Fails if the workitem with specified UID is not 
found or sealed, or has no running pomodoros. Emits `BeforePomodoroComplete` / 
`AfterPomodoroComplete` events with target state `canceled`.
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

## Server strategies

All below strategies are used with server-based event sources only, and are not persisted.

- `Authenticate("<EMAIL>", "<TOKEN>")` - This must be the first strategy sent by the client to 
the server, otherwise the latter closes the communication channel. Note that it doesn't specify 
token's format, leaving it to the authentication implementation.
- `Replay("<AFTER_SEQUENCE>")` - Used for requesting the replay of the strategies from the
server, starting from, but not including, `#AFTER_SEQUENCE`. The server may respond with one
or more messages with event history. 
- `ReplayCompleted("")` - Used by the server to signal the last strategy in the replayed list.
- `Error("<ERROR_CODE>", "<ERROR_MESSAGE>")` - Sent by the server to report an error, e.g. wrong
credentials passed to `Authenticate` strategy. Flowkeeper Desktop raises a UI exception when
executing this strategy. This results in a message popup and a request to file a bug in GitHub.
- `PingStrategy("<UID>", "")` - The client sends this to verify connection to the server. It
expects to receive a `PongStrategy` response with the matching UID immediately after. If the
client doesn't receive a pong in a timely matter, it should switch to Offline / read-only mode.
- `PongStrategy("<UID>", "")` - Sent by the server as a reply to `PingStrategy`. If an Offline 
client receives a matching pong, it should switch back to Online mode.

# Events

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
  - `BeforeSettingsChanged(old_values: dict[str, str], new_values: dict[str, str])`, `AfterSettingsChanged(--//--)`

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

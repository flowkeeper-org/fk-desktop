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
from typing import Callable

# TODO: Move those into the classes where we fire them

BeforeUserCreate = "BeforeUserCreate"
AfterUserCreate = "AfterUserCreate"
BeforeUserDelete = "BeforeUserDelete"
AfterUserDelete = "AfterUserDelete"
BeforeUserRename = "BeforeUserRename"
AfterUserRename = "AfterUserRename"

BeforeBacklogCreate = "BeforeBacklogCreate"
AfterBacklogCreate = "AfterBacklogCreate"
BeforeBacklogDelete = "BeforeBacklogDelete"
AfterBacklogDelete = "AfterBacklogDelete"
BeforeBacklogRename = "BeforeBacklogRename"
AfterBacklogRename = "AfterBacklogRename"
BeforeBacklogReorder = "BeforeBacklogReorder"
AfterBacklogReorder = "AfterBacklogReorder"

BeforeWorkitemCreate = "BeforeWorkitemCreate"
AfterWorkitemCreate = "AfterWorkitemCreate"
BeforeWorkitemComplete = "BeforeWorkitemComplete"
AfterWorkitemComplete = "AfterWorkitemComplete"
BeforeWorkitemStart = "BeforeWorkitemStart"
AfterWorkitemStart = "AfterWorkitemStart"
BeforeWorkitemDelete = "BeforeWorkitemDelete"
AfterWorkitemDelete = "AfterWorkitemDelete"
BeforeWorkitemRename = "BeforeWorkitemRename"
AfterWorkitemRename = "AfterWorkitemRename"
BeforeWorkitemReorder = "BeforeWorkitemReorder"
AfterWorkitemReorder = "AfterWorkitemReorder"
BeforeWorkitemMove = "BeforeWorkitemMove"
AfterWorkitemMove = "AfterWorkitemMove"

BeforePomodoroAdd = "BeforePomodoroAdd"
AfterPomodoroAdd = "AfterPomodoroAdd"
BeforePomodoroRemove = "BeforePomodoroRemove"
AfterPomodoroRemove = "AfterPomodoroRemove"
BeforePomodoroWorkStart = "BeforePomodoroWorkStart"
AfterPomodoroWorkStart = "AfterPomodoroWorkStart"
BeforePomodoroRestStart = "BeforePomodoroRestStart"
AfterPomodoroRestStart = "AfterPomodoroRestStart"
BeforePomodoroComplete = "BeforePomodoroComplete"
AfterPomodoroComplete = "AfterPomodoroComplete"
BeforePomodoroVoided = "BeforePomodoroVoided"
AfterPomodoroVoided = "AfterPomodoroVoided"
BeforePomodoroInterrupted = "BeforePomodoroInterrupted"
AfterPomodoroInterrupted = "AfterPomodoroInterrupted"

TagCreated = "TagCreated"
TagDeleted = "TagDeleted"
TagContentChanged = "TagContentChanged"

SourceMessagesRequested = "SourceMessagesRequested"
SourceMessagesProcessed = "SourceMessagesProcessed"

BeforeMessageProcessed = "BeforeMessageProcessed"
AfterMessageProcessed = "AfterMessageProcessed"

PongReceived = "PongReceived"

BeforeSettingsChanged = "BeforeSettingsChanged"
AfterSettingsChanged = "AfterSettingsChanged"

BeforeTenantRename = "BeforeTenantRename"
AfterTenantRename = "AfterTenantRename"
BeforeTenantDelete = "BeforeTenantDelete"
AfterTenantDelete = "AfterTenantDelete"
BeforeTenantCreate = "BeforeTenantCreate"
AfterTenantCreate = "AfterTenantCreate"

WentOnline = "WentOnline"
WentOffline = "WentOffline"

TimerWorkStart = "TimerWorkStart"
TimerWorkComplete = "TimerWorkComplete"
TimerRestComplete = "TimerRestComplete"


class EmittedEvent:
    event: str
    emitter: object     # TODO: See if we can store a weak reference instead

    def __init__(self, event: str, emitter: object):
        self.event = event
        self.emitter = emitter

    def __str__(self):
        return f'{self.emitter.__class__.__name__}.{self.event}'


# We need this "ad-hoc" callback mechanism for emitters, because our own AbstractEventEmitter subsystem hasn't
# initialized completely yet. It is used by the IntegrationExecutor, which needs to be able to subscribe to
# any events from any emitters immediately after the latter are constructed. So this IntegrationExecutor
# subscribes to all emitters which were constructed BEFORE the IntegrationExecutor was created, and then uses
# this callback mechanism to subscribe to whatever emitters are created after the IntegrationExecutor is created.
ALL_EVENTS: dict[str, EmittedEvent] = dict()
ALL_EVENTS_STR: set[str] = set()
ALL_EMITTERS: set[object] = set()
emitter_added_callback: Callable[[object], None] = None


def set_emitter_added_callback(callback: Callable[[object], None]) -> None:
    global emitter_added_callback
    emitter_added_callback = callback


def register_event(event: str, emitter: object):
    e = EmittedEvent(event, emitter)
    ALL_EVENTS[str(e)] = e
    ALL_EVENTS_STR.add(str(e))
    if emitter not in ALL_EMITTERS:
        ALL_EMITTERS.add(emitter)
        if emitter_added_callback is not None:
            emitter_added_callback(emitter)


def get_all_events() -> set[str]:
    # TODO: See if we can remove duplicates and weak references at the same time here
    return ALL_EVENTS_STR

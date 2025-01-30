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
from typing import Callable

from fk.core import events
from fk.core.abstract_settings import AbstractSettings
from fk.core.abstract_strategy import AbstractStrategy
from fk.core.backlog import Backlog
from fk.core.pomodoro import POMODORO_TYPE_TRACKER
from fk.core.pomodoro_strategies import VoidPomodoroStrategy, FinishTrackingStrategy
from fk.core.strategy_factory import strategy
from fk.core.tag import Tag
from fk.core.tenant import Tenant
from fk.core.user import User
from fk.core.workitem import Workitem


# CreateWorkitem("123-456-789", "234-567-890", "Wake up")
@strategy
class CreateWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _backlog_uid: str
    _workitem_name: str

    def get_backlog_uid(self) -> str:
        return self._backlog_uid

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._backlog_uid = params[1]
        self._workitem_name = params[2]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        user: User = data[self._user_identity]
        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = user[self._backlog_uid]

        if self._workitem_uid in backlog:
            raise Exception(f'Workitem "{self._workitem_uid}" already exists')

        emit(events.BeforeWorkitemCreate, {
            'backlog_uid': self._backlog_uid,
            'workitem_uid': self._workitem_uid,
            'workitem_name': self._workitem_name,
        }, self._carry)
        workitem = Workitem(
            self._workitem_name,
            self._workitem_uid,
            backlog,
            self._when,
        )
        backlog[self._workitem_uid] = workitem
        workitem.item_updated(self._when)   # This will also update the Backlog

        # Update tags
        for tag in workitem.get_tags():
            if tag not in user.get_tags():
                new_tag = Tag(tag, user, self._when)
                user.get_tags()[tag] = new_tag
                emit(events.TagCreated, {"tag": new_tag}, self._carry)
            tag_object = user.get_tags()[tag]
            if workitem not in tag_object.get_workitems():
                tag_object.add_workitem(workitem)
                emit(events.TagContentChanged, {"tag": tag_object}, self._carry)

        emit(events.AfterWorkitemCreate, {
            'workitem': workitem,
        }, self._carry)
        return None, None


def seal_running_pomodoro(strategy_: AbstractStrategy,
                          emit: Callable[[str, dict[str, any], any], None],
                          data: Tenant,
                          workitem: Workitem) -> None:
    for pomodoro in workitem.values():
        if pomodoro.is_running():
            if pomodoro.get_type() == POMODORO_TYPE_TRACKER:
                strategy_.execute_another(emit,
                                          data,
                                          FinishTrackingStrategy,
                                          [workitem.get_uid()])
            else:
                strategy_.execute_another(emit,
                                          data,
                                          VoidPomodoroStrategy,
                                          [workitem.get_uid()])
            return


# DeleteWorkitem("123-456-789")
@strategy
class DeleteWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        params = {
            'workitem': workitem
        }
        emit(events.BeforeWorkitemDelete, params, self._carry)

        seal_running_pomodoro(self, emit, data, workitem)   # Void pomodoros

        workitem.item_updated(self._when)   # Update Backlog

        # Update tags
        tags_to_delete = set[Tag]()
        for tag in user.get_tags().values():
            if workitem in tag.get_workitems():
                tag.remove_workitem(workitem)
                emit(events.TagContentChanged, {"tag": tag}, self._carry)
                if len(tag.get_workitems()) == 0:
                    tags_to_delete.add(tag)
        for tag_to_delete in tags_to_delete:
            del user.get_tags()[tag_to_delete.get_uid()]
            emit(events.TagDeleted, {"tag": tag_to_delete}, self._carry)

        del workitem.get_parent()[self._workitem_uid]

        emit(events.AfterWorkitemDelete, params, self._carry)
        return None, None


# RenameWorkitem("123-456-789", "Wake up")
@strategy
class RenameWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _new_workitem_name: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._new_workitem_name = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if self._new_workitem_name == workitem.get_name():
            # Nothing to do here
            return None, None

        if workitem.is_sealed():
            raise Exception(f'Cannot rename sealed workitem "{self._workitem_uid}"')

        params = {
            'workitem': workitem,
            'old_name': workitem.get_name(),
            'new_name': self._new_workitem_name,
        }
        emit(events.BeforeWorkitemRename, params, self._carry)

        old_tags = workitem.get_tags()
        workitem.set_name(self._new_workitem_name)
        workitem.item_updated(self._when)
        new_tags = workitem.get_tags()

        # Update tags
        for new_tag in new_tags:
            if new_tag not in old_tags:
                # A new tag was added
                if new_tag not in user.get_tags():
                    new_tag_object = Tag(new_tag, user, self._when)
                    user.get_tags()[new_tag] = new_tag_object
                    emit(events.TagCreated, {"tag": new_tag_object}, self._carry)
                tag_object = user.get_tags()[new_tag]
                if workitem not in tag_object.get_workitems():
                    tag_object.add_workitem(workitem)
                    emit(events.TagContentChanged, {"tag": tag_object}, self._carry)
        tags_to_delete = set[Tag]()
        fired_for = set[Tag]()
        for old_tag in old_tags:
            if old_tag not in new_tags:
                # An old tag was removed
                if old_tag in user.get_tags():
                    old_tag_object = user.get_tags()[old_tag]
                    if workitem in old_tag_object.get_workitems():
                        old_tag_object.remove_workitem(workitem)
                        emit(events.TagContentChanged, {"tag": old_tag_object}, self._carry)
                        if len(old_tag_object.get_workitems()) == 0:
                            tags_to_delete.add(old_tag_object)
        for tag_to_delete in tags_to_delete:
            del user.get_tags()[tag_to_delete.get_uid()]
            emit(events.TagDeleted, {"tag": tag_to_delete}, self._carry)

        emit(events.AfterWorkitemRename, params, self._carry)


# CompleteWorkitem("123-456-789", "canceled")
@strategy
class CompleteWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _target_state: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._target_state = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if workitem.is_sealed():
            raise Exception(f'Cannot complete already sealed workitem "{self._workitem_uid}"')

        params = {
            'workitem': workitem,
            'target_state': self._target_state,
        }
        emit(events.BeforeWorkitemComplete, params, self._carry)

        # First void pomodoros if needed
        seal_running_pomodoro(self, emit, data, workitem)

        # Now complete the workitem itself
        workitem.seal(self._target_state, self._when)
        workitem.item_updated(self._when)
        emit(events.AfterWorkitemComplete, params, self._carry)
        return None, None


# ReorderWorkitem("123-456-789", "0")
@strategy
class ReorderWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _new_index: int

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._new_index = int(params[1])

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        backlog: Backlog | None = None
        user: User = data[self._user_identity]
        for b in user.values():
            if self._workitem_uid in b:
                workitem = b[self._workitem_uid]
                backlog = b
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        params = {
            'workitem': workitem,
            'new_index': self._new_index,
        }
        emit(events.BeforeWorkitemReorder, params, self._carry)
        backlog.move_child(workitem, self._new_index)
        backlog.item_updated(self._when)
        emit(events.AfterWorkitemReorder, params, self._carry)
        return None, None


# MoveWorkitem("123-456-789", "234-567-890")
@strategy
class MoveWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _backlog_uid: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def get_backlog_uid(self) -> str:
        return self._backlog_uid

    def __init__(self,
                 seq: int,
                 when: datetime.datetime,
                 user_identity: str,
                 params: list[str],
                 settings: AbstractSettings,
                 carry: any = None):
        super().__init__(seq, when, user_identity, params, settings, carry)
        self._workitem_uid = params[0]
        self._backlog_uid = params[1]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> (str, any):
        workitem: Workitem | None = None
        old_backlog: Backlog | None = None
        user: User = data[self._user_identity]

        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        new_backlog: Backlog = user[self._backlog_uid]

        if old_backlog == new_backlog:
            # Nothing to do
            return None, None

        for b in user.values():
            if self._workitem_uid in b:
                workitem = b[self._workitem_uid]
                old_backlog = b
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        params = {
            'workitem': workitem,
            'old_backlog': old_backlog,
            'new_backlog': new_backlog,
        }
        emit(events.BeforeWorkitemMove, params, self._carry)
        workitem.change_parent(new_backlog)
        old_backlog.item_updated(self._when)
        workitem.item_updated(self._when)   # Update Backlog
        emit(events.AfterWorkitemMove, params, self._carry)
        return None, None

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
from fk.core.category import Category
from fk.core.category_strategies import resolve_categories
from fk.core.pomodoro_strategies import AddInterruptionStrategy
from fk.core.strategy_factory import strategy
from fk.core.tag import Tag
from fk.core.tenant import Tenant
from fk.core.timer_strategies import StopTimerStrategy
from fk.core.user import User
from fk.core.workitem import Workitem


# CreateWorkitem("123-456-789", "234-567-890", "Wake up")
@strategy
class CreateWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _backlog_uid: str
    _workitem_name: str
    _categories: str

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
        if len(params) > 3:
            self._categories = params[3]    # TODO: Allow 4 parameters
        else:
            self._categories = ''

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        user: User = data[self._user_identity]
        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        backlog = user[self._backlog_uid]

        if self._workitem_uid in backlog:
            raise Exception(f'Workitem "{self._workitem_uid}" already exists')

        categories = resolve_categories(self._categories, user)

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
            categories,
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

    def requires_sealing(self) -> bool:
        return True

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
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

        if workitem.has_running_pomodoro():
            # No need to add an interruption like we do in CompleteWorkitemStrategy, because it is deleted anyway
            self.execute_another(emit, data, StopTimerStrategy, [])

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
                data: Tenant) -> None:
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
            return

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

    def requires_sealing(self) -> bool:
        return True

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
                data: Tenant) -> None:
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
        if workitem.has_running_pomodoro():
            if not workitem.get_running_pomodoro().is_long_break() and not workitem.is_tracker():
                self.execute_another(emit,
                                     data,
                                     AddInterruptionStrategy,
                                     [
                                         self.get_workitem_uid(),
                                         f'The item was marked completed before Pomodoro rang'])
            self.execute_another(emit, data, StopTimerStrategy, [])

        # Now complete the workitem itself
        workitem.seal(self._target_state, self._when)
        workitem.item_updated(self._when)
        emit(events.AfterWorkitemComplete, params, self._carry)


# RestoreWorkitem("123-456-789")
@strategy
class RestoreWorkitemStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str

    def get_workitem_uid(self) -> str:
        return self._workitem_uid

    def requires_sealing(self) -> bool:
        return True

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
                data: Tenant) -> None:
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        if not workitem.is_sealed():
            raise Exception(f'Cannot restore a workitem which is not sealed "{self._workitem_uid}"')

        emit(events.BeforeWorkitemRestore, {'workitem': workitem}, self._carry)
        workitem.restore()
        workitem.item_updated(self._when)
        emit(events.AfterWorkitemRestore, {'workitem': workitem}, self._carry)


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
                data: Tenant) -> None:
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
                data: Tenant) -> None:
        workitem: Workitem | None = None
        old_backlog: Backlog | None = None
        user: User = data[self._user_identity]

        if self._backlog_uid not in user:
            raise Exception(f'Backlog "{self._backlog_uid}" not found')
        new_backlog: Backlog = user[self._backlog_uid]

        if old_backlog == new_backlog:
            # Nothing to do
            return

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


# UpdateWorkitemCategories("123-456-789", "remove1;remove2;remove3", "add1;add2;add3")
@strategy
class UpdateWorkitemCategoriesStrategy(AbstractStrategy[Tenant]):
    _workitem_uid: str
    _to_remove: str
    _to_add: str

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
        self._to_remove = params[1]
        self._to_add = params[2]

    def execute(self,
                emit: Callable[[str, dict[str, any], any], None],
                data: Tenant) -> None:
        workitem: Workitem | None = None
        user: User = data[self._user_identity]
        for backlog in user.values():
            if self._workitem_uid in backlog:
                workitem = backlog[self._workitem_uid]
                break

        if workitem is None:
            raise Exception(f'Workitem "{self._workitem_uid}" not found')

        to_add: set[Category] = resolve_categories(self._to_add, user)
        to_remove: set[Category] = resolve_categories(self._to_remove, user)
        existing: set[Category] = workitem.get_categories()

        if len(existing.intersection(to_add)) > 0:
            raise Exception(f'Trying to add duplicate categories to workitem "{self._workitem_uid}"')

        if len(to_remove.difference(existing)) > 0:
            raise Exception(f'Trying to remove non-existing categories from workitem "{self._workitem_uid}"')

        workitem.set_categories(existing.difference(to_remove).union(to_add))

        # TODO: Flesh it out

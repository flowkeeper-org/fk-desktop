#             'newItem': self._create_action("New Item", 'Ins', None, self.create_workitem),
#             'renameItem': self._create_action("Rename Item", 'F2', None, self.rename_selected_workitem),
#             'deleteItem': self._create_action("Delete Item", 'Del', None, self.delete_selected_workitem),
#             'startItem': self._create_action("Start Item", 'Ctrl+S', ":/icons/tool-next.svg", self.start_selected_workitem),
#             'completeItem': self._create_action("Complete Item", 'Ctrl+P', ":/icons/tool-complete.svg", self.complete_selected_workitem),
#             'addPomodoro': self._create_action("Add Pomodoro", 'Ctrl++', None, self.add_pomodoro),
#             'removePomodoro': self._create_action("Remove Pomodoro", 'Ctrl+-', None, self.remove_pomodoro),
#             'showCompleted': self._create_action("Show completed workitems", '', None, self._toggle_show_completed_workitems, True, True),
import datetime
from typing import Callable, Iterable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from fk.core.abstract_data_item import generate_unique_name, generate_uid
from fk.core.abstract_event_source import AbstractEventSource
from fk.core.backlog_strategies import CreateBacklogStrategy


class CreateBacklogAction(QAction):
    _source: AbstractEventSource

    def __init__(self, parent: QWidget, source: AbstractEventSource):
        super().__init__('New Backlog', parent)
        self._source = source
        self.setShortcut('Ctrl+N')
        self.triggered.connect(self.action)

    def action(self):
        prefix: str = datetime.datetime.today().strftime('%Y-%m-%d, %A')   # Locale-formatted
        new_name = generate_unique_name(prefix, self._source.get_data().get_current_user().names())
        self._source.execute(CreateBacklogStrategy, [generate_uid(), new_name], carry='edit')


class Actions:
    _window: QWidget
    _domains: dict[str, object]
    _actions: dict[str, QAction]

    def __init__(self, window: QWidget):
        self._window = window
        self._domains = dict()
        self._actions = dict()

    def add(self,
            name: str,
            text: str,
            shortcut: str,
            icon: str | None,
            member: Callable,
            is_toggle: bool = False,
            is_checked: bool = False) -> QAction:
        res: QAction = QAction(text, self._window)
        res.setObjectName(name)
        if shortcut is not None:
            res.setShortcut(shortcut)
        if icon is not None:
            res.setIcon(QIcon(icon))
        if is_toggle:
            res.setCheckable(True)
            res.setChecked(is_checked)
            res.toggled.connect(lambda checked: self._call(name, member, checked))
        else:
            res.triggered.connect(lambda: self._call(name, member))
        self._window.addAction(res)
        self._actions[name] = res
        return res

    def _call(self, name: str, member: Callable, checked: bool = None):
        [domain, _] = name.split('.')
        if domain in self._domains:
            if checked is None:
                member(self._domains[domain])
            else:
                member(self._domains[domain], checked)
        else:
            raise Exception(f'Attempt to call unbound action {name}')

    def bind(self, domain: str, obj: object):
        self._domains[domain] = obj

    def all(self) -> list[QAction]:
        return list(self._actions.values())

    def __getitem__(self, name: str) -> QAction:
        return self._actions[name]

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    def __iter__(self) -> Iterable[str]:
        return (x for x in self._actions)

    def __len__(self) -> int:
        return len(self._actions)

    def values(self) -> Iterable[QAction]:
        return self._actions.values()

    def keys(self) -> Iterable[str]:
        return self._actions.keys()

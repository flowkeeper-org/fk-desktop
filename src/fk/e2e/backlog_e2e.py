import asyncio
import os

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QCompleter
from assertpy import assert_that

from fk.e2e.abstract_e2e_test import AbstractE2eTest
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.search_completer import SearchBar
from fk.qt.workitem_tableview import WorkitemTableView

TEMP_FILENAME = './backlog-e2e.txt'


class BacklogE2eTest(AbstractE2eTest):
    def __init__(self, app: QApplication):
        super().__init__(app)

    def custom_settings(self) -> dict[str, str]:
        return {
            'FileEventSource.filename': TEMP_FILENAME,
            'Application.show_tutorial': 'False',
            'Application.check_updates': 'False',
            'Pomodoro.default_work_duration': '1',
            'Pomodoro.default_rest_duration': '1',
        }

    def teardown(self) -> None:
        print('Deleting', TEMP_FILENAME)
        os.unlink(TEMP_FILENAME)

    async def _new_backlog(self, name: str) -> None:
        self.keypress(Qt.Key.Key_N, True)   # self.execute_action('backlogs_table.newBacklog')
        await self.instant_pause()
        self.type_text(name)
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()

    async def _start_pomodoro(self) -> None:
        self.keypress(Qt.Key.Key_S, True)   # self.execute_action('workitems_table.startItem')
        await self.instant_pause()

    async def _complete_workitem(self) -> None:
        self.keypress(Qt.Key.Key_P, True)   # self.execute_action('workitems_table.completeItem')
        await self.instant_pause()

    async def _void_pomodoro(self) -> None:
        self.keypress(Qt.Key.Key_V, True)   # self.execute_action('focus.voidPomodoro')
        await self.instant_pause()
        self.close_modal()
        await self.instant_pause()

    async def _add_pomodoro(self) -> None:
        self.keypress(Qt.Key.Key_Plus, True)  # self.execute_action('workitems_table.addPomodoro')
        await self.instant_pause()

    async def _remove_pomodoro(self) -> None:
        self.keypress(Qt.Key.Key_Minus, True)  # self.execute_action('workitems_table.removePomodoro')
        await self.instant_pause()

    async def _new_workitem(self, name: str, pomodoros: int = 0) -> None:
        self.keypress(Qt.Key.Key_Insert)   # self.execute_action('workitems_table.newItem')
        await self.instant_pause()
        self.type_text(name)
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()
        for p in range(pomodoros):
            await self._add_pomodoro()

    async def _find_workitem(self, name: str) -> None:
        self.keypress(Qt.Key.Key_F, True)   # self.execute_action('window.showSearch')
        await self.instant_pause()
        self.type_text(name)
        await self.instant_pause()
        search: SearchBar = self.window().findChild(SearchBar, "search")
        completer = search.completer()
        popup = completer.popup()
        self.keypress(Qt.Key.Key_Down, False, popup)
        self.keypress(Qt.Key.Key_Enter, False, popup)
        await self.instant_pause()

    async def test_backlog_loaded(self):
        main_window = self.window()
        assert_that(main_window.windowTitle()).is_equal_to('Flowkeeper')

        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        backlogs_model = backlogs_table.model()
        assert_that(backlogs_model.rowCount()).is_equal_to(0)

        workitems_table: BacklogTableView = main_window.findChild(WorkitemTableView, "workitems_table")
        workitems_table = workitems_table.model()
        assert_that(workitems_table.rowCount()).is_equal_to(0)

        ################################################################
        # Create a bunch of test backlogs and fill them with workitems #
        ################################################################
        await self._new_backlog('Trip to Italy')
        await self._new_workitem('Workitem 11')
        await self._new_workitem('Workitem 12', 1)
        await self._new_workitem('Workitem 13', 3)
        assert_that(workitems_table.rowCount()).is_equal_to(3)

        await self._new_backlog('House renovation')
        await self._new_workitem('Workitem 21')
        await self._new_workitem('Workitem 22', 1)
        await self._new_workitem('Workitem 23', 3)
        assert_that(workitems_table.rowCount()).is_equal_to(3)

        await self._new_backlog('Long-term stuff')
        await self._new_workitem('Workitem 21')
        await self._new_workitem('Workitem 22', 1)
        await self._new_workitem('Workitem 23', 3)
        assert_that(workitems_table.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-12, Tuesday')
        await self._new_workitem('Workitem 21')
        await self._new_workitem('Workitem 22', 1)
        await self._new_workitem('Workitem 23', 3)
        assert_that(workitems_table.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-13, Wednesday')
        await self._new_workitem('Workitem 21')
        await self._new_workitem('Workitem 22', 1)
        await self._new_workitem('Workitem 23', 3)
        assert_that(workitems_table.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-14, Thursday')
        await self._new_workitem('Generate new screenshots', 2)
        await self._new_workitem('Reply to Peter', 1)
        await self._new_workitem('Slides for the demo', 3)
        await self._new_workitem('Deprecate StartRest strategy', 2)
        await self._new_workitem('Auto-seal in the web frontend', 2)
        await self._new_workitem('Order coffee capsules')
        await self._new_workitem('Call Alex in the afternoon')
        assert_that(workitems_table.rowCount()).is_equal_to(7)

        assert_that(backlogs_model.rowCount()).is_equal_to(6)

        ####################################
        # Complete pomodoros and workitems #
        ####################################
        await self._find_workitem('Generate new screenshots')
        await self._start_pomodoro()
        await asyncio.sleep(0.5)
        await self._void_pomodoro()
        return

        await asyncio.sleep(2.1)
        await self._start_pomodoro()
        await asyncio.sleep(2.1)
        await self._add_pomodoro()
        await self._start_pomodoro()
        await asyncio.sleep(2.1)

        await self._find_workitem('Reply to Peter')
        await self._start_pomodoro()
        await asyncio.sleep(2.1)
        await self._add_pomodoro()
        await self._start_pomodoro()
        await asyncio.sleep(0.5)
        await self._void_pomodoro()
        await self._complete_workitem()

        await self._find_workitem('Slides for the demo')
        await self._start_pomodoro()
        await asyncio.sleep(0.5)
        await self._void_pomodoro()
        await self._start_pomodoro()
        await asyncio.sleep(0.5)
        await self._void_pomodoro()
        await self._complete_workitem()

        await self._find_workitem('Order coffee capsules')
        await self._complete_workitem()

        await self._find_workitem('Call Alex in the afternoon')
        await self._complete_workitem()

        # assert_that(model.index(0, 0).data()).is_equal_to('2024-03-31, Sunday')

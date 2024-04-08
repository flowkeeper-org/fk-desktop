import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from assertpy import assert_that

from fk.e2e.abstract_e2e_test import AbstractE2eTest
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.workitem_tableview import WorkitemTableView

TEMP_FILENAME = './backlog-e2e.txt'


class BacklogE2eTest(AbstractE2eTest):
    def __init__(self, app: QApplication):
        super().__init__(app)

    def custom_settings(self) -> dict[str, str]:
        return {
            'FileEventSource.filename': TEMP_FILENAME,
            'Application.show_tutorial': 'False',
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

    async def _new_workitem(self, name: str, pomodoros: int = 0) -> None:
        self.keypress(Qt.Key.Key_Insert)   # self.execute_action('workitems_table.newItem')
        await self.instant_pause()
        self.type_text(name)
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()
        for p in range(pomodoros):
            self.keypress(Qt.Key.Key_Plus, True)  # self.execute_action('workitems_table.addPomodoro')
            await self.instant_pause()

    async def _find_workitem(self, name: str) -> None:
        self.keypress(Qt.Key.Key_F, True)   # self.execute_action('window.showSearch')
        await self.instant_pause()
        self.type_text(name)
        await self.instant_pause()
        self.keypress(Qt.Key.Key_Down)  # TODO: This doesn't work
        await self.instant_pause()
        self.keypress(Qt.Key.Key_Enter)
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

        await self._find_workitem('Reply to Peter')


        # assert_that(count).is_equal_to(10)
        # assert_that(model.index(0, 0).data()).is_equal_to('2024-03-31, Sunday')
        # assert_that(model.index(1, 0).data()).is_equal_to('27/10/23')
        # assert_that(model.index(2, 0).data()).is_equal_to('Flowkeeper')
        #
        # self.mouse_click_row(table, 6)
        # print(f'DEBUG: Clicked on a random backlog')
        #
        # await asyncio.sleep(0.1)
        # #t.keypress(Qt.Key.Key_N, True)
        # #print('DEBUG: Typed')
        # self.get_focused()
        # #await asyncio.sleep(0.1)
        # #t.keypress(Qt.Key.Key_Enter)

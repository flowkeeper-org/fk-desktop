import asyncio
import os

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QCompleter
from assertpy import assert_that

from fk.core.pomodoro import Pomodoro
from fk.core.workitem import Workitem
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
            'Application.play_alarm_sound': 'False',
            'Application.play_rest_sound': 'False',
            'Application.play_tick_sound': 'False',
        }

    def teardown(self) -> None:
        self.info(f'Deleting {TEMP_FILENAME}')
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

    async def _select_backlog(self, name: str) -> None:
        main_window = self.window()
        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        backlogs_model = backlogs_table.model()
        for i in range(backlogs_model.rowCount()):
            if backlogs_model.index(i, 0).data() == name:
                self.mouse_click_row(backlogs_table, i)
                await self.instant_pause()
                return

    async def test_01_create_backlogs(self):
        ##################
        # General checks #
        ##################
        self.info('General checks')
        main_window = self.window()
        assert_that(main_window.windowTitle()).is_equal_to('Flowkeeper')

        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        backlogs_model = backlogs_table.model()
        assert_that(backlogs_model.rowCount()).is_equal_to(0)

        workitems_table: BacklogTableView = main_window.findChild(WorkitemTableView, "workitems_table")
        workitems_model = workitems_table.model()
        assert_that(workitems_model.rowCount()).is_equal_to(0)

        ################################################################
        # Create a bunch of test backlogs and fill them with workitems #
        ################################################################
        self.info('Create a bunch of test backlogs and fill them with workitems')
        await self._new_backlog('Trip to Italy')
        await self._new_workitem('Workitem 11')
        await self._new_workitem('Workitem 12', 1)
        await self._new_workitem('Workitem 13', 3)
        assert_that(workitems_model.rowCount()).is_equal_to(3)

        await self._new_backlog('House renovation')
        await self._new_workitem('Workitem 21')
        await self._new_workitem('Workitem 22', 1)
        await self._new_workitem('Workitem 23', 3)
        assert_that(workitems_model.rowCount()).is_equal_to(3)

        await self._new_backlog('Long-term stuff')
        await self._new_workitem('Workitem 31')
        await self._new_workitem('Workitem 32', 1)
        await self._new_workitem('Workitem 33', 3)
        assert_that(workitems_model.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-12, Tuesday')
        await self._new_workitem('Workitem 41')
        await self._new_workitem('Workitem 42', 1)
        await self._new_workitem('Workitem 43', 3)
        assert_that(workitems_model.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-13, Wednesday')
        await self._new_workitem('Workitem 51')
        await self._new_workitem('Workitem 52', 1)
        await self._new_workitem('Workitem 53', 3)
        assert_that(workitems_model.rowCount()).is_equal_to(3)

        await self._new_backlog('2024-03-14, Thursday')
        await self._new_workitem('Generate new screenshots', 2)
        await self._new_workitem('Reply to Peter', 1)
        await self._new_workitem('Slides for the demo', 3)
        await self._new_workitem('Deprecate StartRest strategy', 2)
        await self._new_workitem('Auto-seal in the web frontend', 2)
        await self._new_workitem('Order coffee capsules')
        await self._new_workitem('Call Alex in the afternoon')
        assert_that(workitems_model.rowCount()).is_equal_to(7)

        assert_that(backlogs_model.rowCount()).is_equal_to(6)

        ####################################
        # Complete pomodoros and workitems #
        ####################################
        self.info('Complete pomodoros and workitems')
        await self._find_workitem('Generate new screenshots')
        await self._start_pomodoro()
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

    def assert_actions_enabled(self, names: list[str]) -> None:
        for name in names:
            assert_that(self.is_action_enabled(name), f'Action {name} should be enabled').is_true()

    def assert_actions_disabled(self, names: list[str]) -> None:
        for name in names:
            assert_that(self.is_action_enabled(name), f'Action {name} should be disabled').is_false()

    async def test_02_actions_visibility(self):
        main_window = self.window()
        workitems_table: BacklogTableView = main_window.findChild(WorkitemTableView, "workitems_table")

        ############################################################
        # Check actions on a new workitem with available pomodoros #
        ############################################################
        self.info('Check actions on a new workitem with available pomodoros')
        await self._find_workitem('Deprecate StartRest strategy')
        workitem: Workitem = workitems_table.get_current()
        assert_that(workitem.get_name()).is_equal_to('Deprecate StartRest strategy')
        assert_that(len(workitem)).is_equal_to(2)
        for p in workitem.values():
            assert_that(p.is_startable()).is_true()

        # All actions:
        # application.settings
        # application.quit
        # application.import
        # application.export
        # application.tutorial
        # application.about
        # backlogs_table.newBacklog
        # backlogs_table.renameBacklog
        # backlogs_table.deleteBacklog
        # workitems_table.newItem
        # workitems_table.renameItem
        # workitems_table.deleteItem
        # workitems_table.startItem
        # workitems_table.completeItem
        # workitems_table.addPomodoro
        # workitems_table.removePomodoro
        # workitems_table.showCompleted
        # focus.voidPomodoro
        # focus.nextPomodoro
        # focus.completeItem
        # focus.showFilter
        def assert_backlog_actions_enabled():
            self.assert_actions_enabled([
                'backlogs_table.newBacklog',
                'backlogs_table.renameBacklog',
                'backlogs_table.deleteBacklog',
                'workitems_table.newItem',
                'workitems_table.showCompleted',
            ])

        assert_backlog_actions_enabled()
        self.assert_actions_enabled([
            'workitems_table.renameItem',
            'workitems_table.deleteItem',
            'workitems_table.startItem',
            'workitems_table.completeItem',
            'workitems_table.addPomodoro',
            'workitems_table.removePomodoro',
        ])
        self.assert_actions_disabled([
            'focus.voidPomodoro',
        ])

        #########################################################
        # Check actions on a new workitem without any pomodoros #
        #########################################################
        self.info('Check actions on a new workitem without any pomodoros')
        await self._find_workitem('Workitem 51')
        workitem = workitems_table.get_current()
        assert_that(workitem.get_name()).is_equal_to('Workitem 51')
        assert_that(len(workitem)).is_equal_to(0)

        assert_backlog_actions_enabled()
        self.assert_actions_enabled([
            'workitems_table.renameItem',
            'workitems_table.deleteItem',
            'workitems_table.completeItem',
            'workitems_table.addPomodoro',
        ])
        self.assert_actions_disabled([
            'workitems_table.removePomodoro',
            'workitems_table.startItem',
            'focus.voidPomodoro',
        ])

        ###############################################################
        # Check actions on a new workitem without available pomodoros #
        ###############################################################
        self.info('Check actions on a new workitem without available pomodoros')
        await self._find_workitem('Generate new screenshots')
        workitem = workitems_table.get_current()
        assert_that(workitem.get_name()).is_equal_to('Generate new screenshots')
        assert_that(len(workitem)).is_equal_to(3)
        for p in workitem.values():
            assert_that(p.is_startable()).is_false()

        assert_backlog_actions_enabled()
        self.assert_actions_enabled([
            'workitems_table.renameItem',
            'workitems_table.deleteItem',
            'workitems_table.completeItem',
            'workitems_table.addPomodoro',
        ])
        self.assert_actions_disabled([
            'workitems_table.removePomodoro',
            'workitems_table.startItem',
            'focus.voidPomodoro',
        ])

        ########################################################################
        # Check actions on a completed workitem, even with available pomodoros #
        ########################################################################
        self.info('Check actions on a completed workitem, even with available pomodoros')
        await self._find_workitem('Slides for the demo')
        workitem = workitems_table.get_current()
        assert_that(workitem.get_name()).is_equal_to('Slides for the demo')
        assert_that(len(workitem)).is_equal_to(3)
        startable_count = 0
        for p in workitem.values():
            if p.is_startable():
                startable_count += 1
        assert_that(startable_count).is_equal_to(1)

        assert_backlog_actions_enabled()
        self.assert_actions_enabled([
            'workitems_table.deleteItem',
        ])
        self.assert_actions_disabled([
            'workitems_table.addPomodoro',
            'workitems_table.completeItem',
            'workitems_table.renameItem',
            'workitems_table.removePomodoro',
            'workitems_table.startItem',
            'focus.voidPomodoro',
        ])

        #################################################
        # Select another backlog to unselect a workitem #
        #################################################
        self.info('Select another backlog to unselect a workitem')
        await self._select_backlog('Trip to Italy')
        workitem = workitems_table.get_current()
        assert_that(workitem, 'Selecting another backlog should deselect workitem').is_none()

        assert_backlog_actions_enabled()
        self.assert_actions_disabled([
            'workitems_table.deleteItem',
            'workitems_table.addPomodoro',
            'workitems_table.completeItem',
            'workitems_table.renameItem',
            'workitems_table.removePomodoro',
            'workitems_table.startItem',
            'focus.voidPomodoro',
        ])

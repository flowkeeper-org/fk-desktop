import asyncio
import os

from PySide6.QtCore import Qt
from assertpy import assert_that

from fk.desktop.application import Application
from fk.e2e.abstract_e2e_test import AbstractE2eTest
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.search_completer import SearchBar

TEMP_FILENAME = './backlog-e2e.txt'
POMODORO_WORK_DURATION = 0.25  # seconds
POMODORO_REST_DURATION = 0.25  # seconds


class ServerE2eTest(AbstractE2eTest):
    def __init__(self, app: Application):
        super().__init__(app)

    def custom_settings(self) -> dict[str, str]:
        return {
            'FileEventSource.filename': TEMP_FILENAME,
            'Application.show_tutorial': 'False',
            'Application.check_updates': 'False',
            'Application.show_window_title': 'True',
            'Pomodoro.default_work_duration': str(POMODORO_WORK_DURATION),
            'Pomodoro.default_rest_duration': str(POMODORO_REST_DURATION),
            'Application.play_alarm_sound': 'False',
            'Application.play_rest_sound': 'False',
            'Application.play_tick_sound': 'False',
            'Logger.filename': 'backlog-e2e.log',
            'Logger.level': 'DEBUG',
        }

    def teardown(self) -> None:
        super().teardown()
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

    async def _wait_pomodoro_complete(self) -> None:
        await asyncio.sleep(POMODORO_WORK_DURATION)
        await asyncio.sleep(POMODORO_REST_DURATION)
        await self.instant_pause()

    async def _wait_mid_pomodoro(self) -> None:
        await asyncio.sleep(POMODORO_WORK_DURATION * 0.75)

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
        # noinspection PyTypeChecker
        search: SearchBar = self.window().findChild(SearchBar, "search")
        completer = search.completer()
        popup = completer.popup()
        self.keypress(Qt.Key.Key_Down, False, popup)
        self.keypress(Qt.Key.Key_Enter, False, popup)
        await self.instant_pause()

    async def _select_backlog(self, name: str) -> int:
        # noinspection PyTypeChecker
        backlogs_table: BacklogTableView = self.window().findChild(BacklogTableView, "backlogs_table")
        backlogs_model = backlogs_table.model()
        for i in range(backlogs_model.rowCount()):
            if backlogs_model.index(i, 0).data() == name:
                await self.mouse_click_row(backlogs_table, i)
                return i
        return -1

    def assert_actions_enabled(self, names: list[str]) -> None:
        for name in names:
            assert_that(self.is_action_enabled(name), f'Action {name} should be enabled').is_true()

    def assert_actions_disabled(self, names: list[str]) -> None:
        for name in names:
            assert_that(self.is_action_enabled(name), f'Action {name} should be disabled').is_false()

    async def test_01_create_backlogs(self):
        ##################
        # General checks #
        ##################
        self.info('General checks')
        assert_that(self.window().windowTitle()).is_equal_to('Flowkeeper')

        self.start_server('e2e', '9999', False)

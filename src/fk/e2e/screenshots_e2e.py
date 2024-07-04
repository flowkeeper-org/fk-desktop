import asyncio
import os

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QTabWidget, QComboBox, QWidget

from fk.desktop.application import Application
from fk.e2e.abstract_e2e_test import AbstractE2eTest, GALLERY_FILENAME
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.search_completer import SearchBar

TEMP_FILENAME = './screenshots-e2e.txt'
POMODORO_WORK_DURATION = 0.25  # seconds
POMODORO_REST_DURATION = 0.25  # seconds


class ScreenshotE2eTest(AbstractE2eTest):
    def __init__(self, app: Application):
        super().__init__(app)

    def setup(self) -> None:
        if os.path.isfile(GALLERY_FILENAME):
            os.unlink(GALLERY_FILENAME)

    def custom_settings(self) -> dict[str, str]:
        return {
            'FileEventSource.filename': TEMP_FILENAME,
            'Application.show_tutorial': 'False',
            'Application.check_updates': 'False',
            'Pomodoro.default_work_duration': str(POMODORO_WORK_DURATION),
            'Pomodoro.default_rest_duration': str(POMODORO_REST_DURATION),
            'Application.play_alarm_sound': 'False',
            'Application.play_rest_sound': 'False',
            'Application.play_tick_sound': 'False',
            'Logger.filename': 'backlog-e2e.log',
            'Logger.level': 'DEBUG',
            'Application.window_height': '680',
            'Application.window_splitter_width': '260',
            'Application.window_width': '820',
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
        main_window = self.window()
        # noinspection PyTypeChecker
        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        backlogs_model = backlogs_table.model()
        for i in range(backlogs_model.rowCount()):
            if backlogs_model.index(i, 0).data() == name:
                self.mouse_click_row(backlogs_table, i)
                await self.instant_pause()
                return i
        return -1

    async def test_01_create_backlogs(self):
        ################################################################
        # Create a bunch of test backlogs and fill them with workitems #
        ################################################################
        await self._new_backlog('Trip to Italy')

        await self._new_backlog('House renovation')
        await self._new_backlog('Long-term stuff')
        await self._new_backlog('2024-03-12, Tuesday')
        await self._new_backlog('2024-03-13, Wednesday')
        await self._new_backlog('2024-03-14, Thursday')

        self.keypress(Qt.Key.Key_F10)
        await self.instant_pause()
        settings_tabs: QTabWidget = self.window().findChild(QTabWidget, "settings_tabs")
        settings_tabs.setCurrentIndex(1)
        await self.instant_pause()
        source_type_dropdown: QComboBox = self.window().findChild(QComboBox, "Source.type")
        source_type_dropdown.setCurrentIndex(0)
        await self.instant_pause()
        self.take_screenshot('03-settings-connection-offline')

        source_type_dropdown.setCurrentIndex(2)
        await self.instant_pause()
        self.take_screenshot('04-settings-connection-self-hosted')

        source_type_dropdown.setCurrentIndex(1)
        await self.instant_pause()
        auth_type_dropdown: QComboBox = self.window().findChild(QComboBox, "WebsocketEventSource.auth_type")
        self.mouse_click(auth_type_dropdown)    # Doesn't work
        await self.instant_pause()

        self.take_screenshot('05-settings-connection-flowkeeper-org')

        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        await self._new_workitem('Generate new screenshots', 2)
        await self._new_workitem('Reply to Peter', 1)
        await self._new_workitem('Slides for the demo', 3)
        await self._new_workitem('Deprecate StartRest strategy', 2)
        await self._new_workitem('Auto-seal in the web frontend', 2)
        await self._new_workitem('Order coffee capsules')
        await self._new_workitem('Call Alex in the afternoon')

        ####################################
        # Complete pomodoros and workitems #
        ####################################
        await self._find_workitem('Generate new screenshots')
        await self._start_pomodoro()

        self.take_screenshot('02-pomodoro')

        await self._wait_pomodoro_complete()
        await self._start_pomodoro()
        await self._wait_pomodoro_complete()
        await self._add_pomodoro()
        await self._start_pomodoro()
        await self._wait_pomodoro_complete()

        await self._find_workitem('Reply to Peter')
        await self._start_pomodoro()
        await self._wait_pomodoro_complete()
        await self._add_pomodoro()
        await self._start_pomodoro()
        await self._wait_mid_pomodoro()
        await self._void_pomodoro()
        await self._complete_workitem()

        await self._find_workitem('Slides for the demo')
        await self._start_pomodoro()
        await self._wait_mid_pomodoro()
        await self._void_pomodoro()
        await self._start_pomodoro()
        await self._wait_mid_pomodoro()
        await self._void_pomodoro()
        await self._complete_workitem()

        await self._find_workitem('Order coffee capsules')
        await self._complete_workitem()

        await self._find_workitem('Call Alex in the afternoon')
        await self._complete_workitem()

        await self._find_workitem('Generate new screenshots')

        backlogs_table: BacklogTableView = self.window().findChild(BacklogTableView, "backlogs_table")
        backlogs_table._menu.popup(backlogs_table.mapToGlobal(QPoint(100, 400)))
        await self.instant_pause()
        self.take_screenshot('01-backlog')
        backlogs_table._menu.close()


import asyncio
import datetime
import os

from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtWidgets import QTabWidget, QComboBox, QLineEdit, QCheckBox, QPushButton, QTableWidget

from fk.core.abstract_data_item import generate_uid
from fk.core.abstract_settings import S
from fk.core.interruption import Interruption
from fk.core.pomodoro import Pomodoro, POMODORO_TYPE_NORMAL
from fk.core.pomodoro_strategies import AddInterruptionStrategy
from fk.core.timer_strategies import StartTimerStrategy, StopTimerStrategy
from fk.core.workitem import Workitem
from fk.core.workitem_strategies import CompleteWorkitemStrategy
from fk.desktop.application import Application
from fk.e2e.abstract_e2e_test import AbstractE2eTest, WINDOW_GALLERY_FILENAME, FULLSCREEN_GALLERY_FILENAME, \
    WINDOW_BORDER_GALLERY_FILENAME
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.search_completer import SearchBar
from fk.qt.workitem_tableview import WorkitemTableView
from fk.tests.test_utils import random

TEMP_FILENAME = './screenshots-e2e.txt'
POMODORO_WORK_DURATION = 3  # seconds
POMODORO_REST_DURATION = 3  # seconds


class ScreenshotFastTest(AbstractE2eTest):
    def __init__(self, app: Application):
        super().__init__(app)

    def setup(self) -> None:
        if os.path.isfile(WINDOW_GALLERY_FILENAME):
            os.unlink(WINDOW_GALLERY_FILENAME)
        if os.path.isfile(WINDOW_BORDER_GALLERY_FILENAME):
            os.unlink(WINDOW_BORDER_GALLERY_FILENAME)
        if os.path.isfile(FULLSCREEN_GALLERY_FILENAME):
            os.unlink(FULLSCREEN_GALLERY_FILENAME)

    def custom_settings(self) -> dict[str, str]:
        custom = {
            S.FILEEVENTSOURCE_FILENAME: TEMP_FILENAME,
            S.APPLICATION_SHOW_TUTORIAL: 'False',
            S.APPLICATION_SHOW_WINDOW_TITLE: 'False',
            S.APPLICATION_CHECK_UPDATES: 'False',
            S.POMODORO_LONG_BREAK_ALGORITHM: 'never',
            S.POMODORO_DEFAULT_WORK_DURATION: str(POMODORO_WORK_DURATION),
            S.POMODORO_DEFAULT_REST_DURATION: str(POMODORO_REST_DURATION),
            S.APPLICATION_PLAY_ALARM_SOUND: 'False',
            S.APPLICATION_PLAY_REST_SOUND: 'False',
            S.APPLICATION_PLAY_TICK_SOUND: 'False',
            S.APPLICATION_PLAY_NOTIFICATION_SOUND: 'False',
            S.LOGGER_FILENAME: 'backlog-e2e.log',
            S.LOGGER_LEVEL: 'DEBUG',
            S.APPLICATION_WINDOW_HEIGHT: '680',
            S.APPLICATION_WINDOW_SPLITTER_WIDTH: '260',
            S.APPLICATION_WINDOW_WIDTH: '820',
            S.APPLICATION_THEME: 'mixed',
            S.APPLICATION_TRAY_ICON_FLAVOR: 'thin-dark',
            #S.APPLICATION_LAST_VERSION: self.get_application()._current_version,
            S.APPLICATION_LAST_VERSION: '0.0.1',
            S.INTEGRATION_CALLBACKS: '{"FileEventSource.AfterBacklogCreate": '
                                     '"echo \\"Created backlog {backlog.get_uid()}\\""}',
            S.APPLICATION_SHOW_CLICK_HERE_HINT: 'True',
        }
        if os.name == 'nt':
            custom[S.APPLICATION_FONT_MAIN_SIZE] = '10'
            custom[S.APPLICATION_FONT_HEADER_FAMILY] = 'Segoe UI Light'
        return custom

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

    async def _wait_long_pomodoro(self) -> None:
        await asyncio.sleep(15)

    async def _complete_workitem(self, name: str) -> None:
        source = self.get_application().get_source_holder().get_source()
        for w in source.workitems():
            if w.get_name() == name:
                source.execute(CompleteWorkitemStrategy, [w.get_uid(), "finished"])
                await self.instant_pause()

    async def _void_pomodoro(self, name: str) -> None:
        source = self.get_application().get_source_holder().get_source()
        for w in source.workitems():
            if w.get_name() == name:
                source.execute(AddInterruptionStrategy, [w.get_uid(), f'Pomodoro voided'])
                source.execute(StopTimerStrategy, [])
                await self.instant_pause()

    async def _stop_tracking(self) -> None:
        self.keypress(Qt.Key.Key_S, True)
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
                await self.mouse_click_row(backlogs_table, i)
                return i
        return -1

    async def _select_tag(self, name: str) -> bool:
        main_window = self.window()
        # noinspection PyTypeChecker
        tag_widget: QPushButton = main_window.findChild(QPushButton, f"#{name.lower()}")
        if tag_widget is not None:
            tag_widget.click()
            return True
        else:
            return False

    async def test_01_wizard(self):
        await self.instant_pause()
        await self._wait_mid_pomodoro()
        self.take_screenshot('26-focus-window-types')
        self.click_button(name='qt_wizard_commit')
        await self.instant_pause()
        self.take_screenshot('27-tray-icon-types')
        self.click_button(name='qt_wizard_finish')
        await self.instant_pause()

    async def _normal_settings(self):
        self.get_application().get_settings().set({
            S.APPLICATION_SHOW_CLICK_HERE_HINT: 'False',
            S.FILEEVENTSOURCE_FILENAME: './src/fk/e2e/fixtures/screenshots-basic.txt',
        })
        await self.instant_pause()

    async def test_02_stats(self):
        await self._normal_settings()
        self._generate_pomodoros_for_stats()
        self.keypress(Qt.Key.Key_F9)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        self.take_screenshot('13-stats-week')
        self.keypress(Qt.Key.Key_M, True)
        await self.instant_pause()
        self.take_screenshot('14-stats-month')
        self.keypress(Qt.Key.Key_Y, True)
        await self.instant_pause()
        self.take_screenshot('15-stats-year')
        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

    def _generate_pomodoros_for_stats(self):
        source = self.get_application().get_source_holder().get_source()
        for b in source.backlogs():
            if b.get_name() == '2024-03-13, Wednesday':
                now = datetime.datetime.now(datetime.timezone.utc)
                uid = generate_uid()
                workitem = Workitem('Huge', uid, b, now, [])
                b[uid] = workitem
                self._emulate_year(workitem, now - datetime.timedelta(days=365))

    def _emulate_year(self, workitem: Workitem, start_date: datetime.datetime):
        for day in range(365):
            now = start_date + datetime.timedelta(days=day)
            now = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            self._emulate_day(workitem, now, day)

    def _emulate_day(self, workitem: Workitem, start_date: datetime.datetime, day: int):
        weekday = start_date.weekday()
        if weekday < 5 or random() < 0.05:
            avg_pomos = 10 + round(day / 100) - weekday
            num_pomos = round(avg_pomos * (1 + (random() - 0.5) / 5))
            now = start_date + datetime.timedelta(minutes=round(60 * 7 + random() * 180))
            for p in range(num_pomos):
                uid = generate_uid()
                state_selector = random()
                num_interruptions = 0
                if state_selector < 0.1 + (365 - day) / 1200:
                    state = 'new'
                    num_interruptions = random() * 3
                elif state_selector < 0.5 + day / 900:
                    state = 'finished'
                else:
                    state = 'new'
                workitem[uid] = Pomodoro(p + 1, True, state, 25 * 60, 5 * 60, POMODORO_TYPE_NORMAL, uid, workitem, now)
                for _ in range(round(num_interruptions)):
                    int_uid = generate_uid()
                    workitem[uid][int_uid] = Interruption("Pomodoro voided" if random() < 0.5 else None, None, False, int_uid, workitem[uid], now)
                now = now + datetime.timedelta(minutes=round(random() * 20))

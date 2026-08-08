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


class ScreenshotE2eTest(AbstractE2eTest):
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
            # S.APPLICATION_LAST_VERSION: self.get_application()._current_version,
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

    async def _wait_end_of_work(self) -> None:
        await asyncio.sleep(POMODORO_WORK_DURATION * 1.1)

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

    async def _new_workitem(self, name: str, pomodoros: int = 0, category = None) -> None:
        if category is not None:
            self.get_application().get_settings().set({S.APPLICATION_DEFAULT_WORKITEM_CATEGORY: category})
            await self.instant_pause()
        self.keypress(Qt.Key.Key_Insert)   # self.execute_action('workitems_table.newItem')
        await self.instant_pause()
        self.type_text(name)
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()
        for p in range(pomodoros):
            await self._add_pomodoro()
        if category is not None:
            self.get_application().get_settings().set({S.APPLICATION_DEFAULT_WORKITEM_CATEGORY: 'ask'})
            await self.instant_pause()

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

    async def _select_category(self, uid: str = '') -> bool:
        self.get_application().get_settings().set({S.APPLICATION_SELECTED_CATEGORY: uid})
        return True

    async def test_01_screenshots(self):
        await self.instant_pause()
        await self._wait_mid_pomodoro()
        await self._wait_mid_pomodoro()
        await self._wait_mid_pomodoro()
        self.take_screenshot('26-focus-window-types')
        # self.click_button(name='__qt__passive_wizardbutton1')
        self.click_button(name='qt_wizard_commit')
        await self.instant_pause()
        self.take_screenshot('27-tray-icon-types')
        self.click_button(name='qt_wizard_finish')
        await self.instant_pause()

        self.get_application().get_settings().set({S.APPLICATION_SHOW_CLICK_HERE_HINT: 'False'})
        await self.instant_pause()

        main_window = self.window()
        self.center_window()
        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        workitems_table: WorkitemTableView = main_window.findChild(WorkitemTableView, "workitems_table")

        ################################################################
        # Create a bunch of test backlogs and fill them with workitems #
        ################################################################
        await self._new_backlog('Trip to Italy')

        await self._new_backlog('House renovation')
        await self._new_backlog('Long-term stuff')
        await self._new_backlog('2024-03-12, Tuesday')
        await self._new_backlog('2024-03-13, Wednesday')
        await self._new_backlog('2024-03-14, Thursday')

        self._generate_pomodoros_for_stats()
        await self.instant_pause()
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

        self.get_application().get_settings().set({S.POMODORO_LONG_BREAK_ALGORITHM: 'simple', S.POMODORO_START_NEXT_AUTOMATICALLY: 'True'})
        await self.instant_pause()

        self.keypress(Qt.Key.Key_F10)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        settings_tabs: QTabWidget = self.window().findChild(QTabWidget, "settings_tabs")
        settings_tabs.setCurrentIndex(2)
        await self.instant_pause()
        data_file_edit: QLineEdit = self.window().findChild(QLineEdit, "FileEventSource.filename-edit")
        data_file_edit.selectAll()
        await self.instant_pause()
        self.take_screenshot('03-settings-connection-offline')

        settings_tabs.setCurrentIndex(1)
        await self.instant_pause()
        series_check: QCheckBox = self.window().findChild(QCheckBox, S.POMODORO_START_NEXT_AUTOMATICALLY)
        series_check.setChecked(True)
        await self.instant_pause()
        self.take_screenshot('04-settings-long-breaks')
        series_check.setChecked(False)
        await self.instant_pause()

        settings_tabs.setCurrentIndex(5)
        await self.instant_pause()
        sound_alarm_check: QCheckBox = self.window().findChild(QCheckBox, S.APPLICATION_PLAY_ALARM_SOUND)
        sound_alarm_check.setChecked(True)
        await self.instant_pause()
        sound_alarm_check: QCheckBox = self.window().findChild(QCheckBox, S.APPLICATION_PLAY_REST_SOUND)
        sound_alarm_check.setChecked(True)
        await self.instant_pause()
        sound_file_edit: QLineEdit = self.window().findChild(QLineEdit, "Application.alarm_sound_file-edit")
        sound_file_edit.selectAll()
        await self.instant_pause()
        self.take_screenshot('07-settings-audio')
        sound_alarm_check.setChecked(False)
        await self.instant_pause()

        settings_tabs.setCurrentIndex(6)
        self.window().setFixedWidth(800)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        integration_callbacks: QTableWidget = self.window().findChild(QTableWidget, S.INTEGRATION_CALLBACKS)
        integration_callbacks.selectRow(6)
        await self.instant_pause()
        self.take_screenshot('21-settings-integration')

        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        self.get_application().get_settings().set({
            S.POMODORO_LONG_BREAK_ALGORITHM: 'never',
            S.POMODORO_START_NEXT_AUTOMATICALLY: 'False',
        })
        await self.instant_pause()

        # Select a category
        await self._select_category('#wg_123')
        await self.instant_pause()

        await self._new_workitem('Generate new screenshots for #Flowkeeper', 2, '#wg_123_1')
        await self._new_workitem('Reply to Peter', 1, '#wg_123_3')
        await self._new_workitem('Slides for #Flowkeeper demo', 3, '#wg_123_2')
        await self._new_workitem('#Flowkeeper: Deprecate StartRest strategy', 2, '#wg_123_2')
        await self._new_workitem('#Flowkeeper: Auto-seal in the web frontend', 2, '#wg_123_3')
        await self._new_workitem('#Followup: Call Alex in the afternoon', 0, '#wg_123_3')

        await self._select_category()
        await self.instant_pause()

        ####################################
        # Complete pomodoros and workitems #
        ####################################
        await self._find_workitem('Generate new screenshots for #Flowkeeper')
        await self._start_pomodoro()
        self.center_window()
        await self.instant_pause()

        self.take_screenshot('02-pomodoro')

        await self._wait_pomodoro_complete()
        self.center_window()
        await self.instant_pause()
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
        await self._wait_end_of_work()
        self.take_screenshot('28-fullscreen-break')
        await self._void_pomodoro('Reply to Peter')
        await self._complete_workitem('Reply to Peter')
        await self.longer_pause()

        # Demo the tracker items -- start another WI in the past
        await self._find_workitem('#Followup: Call Alex in the afternoon')
        await self._start_pomodoro()
        await self._wait_long_pomodoro()
        source = self.get_application().get_source_holder().get_source()
        source.execute(StopTimerStrategy, [])
        await self.longer_pause()

        await self._new_workitem('Order coffee capsules')
        await self._find_workitem('Order coffee capsules')
        await self._complete_workitem('Order coffee capsules')

        await self._find_workitem('Slides for #Flowkeeper demo')
        await self._start_pomodoro()
        await self._wait_mid_pomodoro()
        await self._void_pomodoro('Slides for #Flowkeeper demo')

        # Select a category
        await self._select_category('#wg_123')
        await self.instant_pause()
        self.take_screenshot('29-category-selected')
        await self.instant_pause()
        await self._select_category()
        await self.instant_pause()

        # Category list
        self.keypress(Qt.Key.Key_F5)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        self.take_screenshot('30-categories')
        await self.instant_pause()
        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        # Tags
        await self._select_tag('Flowkeeper')
        await self.instant_pause()
        self.take_screenshot('20-tags')
        await self.instant_pause()
        await self._find_workitem('Slides for #Flowkeeper demo')
        await self.instant_pause()

        # Take two "main" screenshots right in the middle of this pomodoro
        settings = self.get_application().get_settings()
        old_value_work = settings.get(S.POMODORO_DEFAULT_WORK_DURATION)
        old_value_rest = settings.get(S.POMODORO_DEFAULT_REST_DURATION)
        old_value_style = settings.get(S.APPLICATION_TIMER_UI_MODE)
        old_value_theme = settings.get(S.APPLICATION_THEME)
        old_focus_flavor = settings.get(S.APPLICATION_FOCUS_FLAVOR)
        old_gradient = settings.get(S.APPLICATION_EYECANDY_GRADIENT)
        old_eyecandy_type = settings.get(S.APPLICATION_EYECANDY_TYPE)
        settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: '1500',
            S.POMODORO_DEFAULT_REST_DURATION: '300',
            S.APPLICATION_TIMER_UI_MODE: 'keep',
            S.APPLICATION_THEME: 'light',
            S.APPLICATION_EYECANDY_GRADIENT: 'OverSun',
        })

        # Re-enable categories
        await self._select_category('#wg_123')
        await self.instant_pause()

        # Start a Pomodoro in the past
        source = self.get_application().get_source_holder().get_source()
        workitem_id = None
        for w in source.workitems():
            if w.get_name() == 'Slides for #Flowkeeper demo':
                workitem_id = w.get_uid()
        source.execute_prepared_strategy(StartTimerStrategy(
            1,
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=670),
            'user@local.host',
            [workitem_id, '1500', '300'],
            settings))
        await self._wait_mid_pomodoro()
        await self._wait_mid_pomodoro()
        await self._wait_mid_pomodoro()
        await self._wait_mid_pomodoro()

        self.take_screenshot('18-main-light')

        settings.set({
            S.APPLICATION_THEME: 'dark',
            S.APPLICATION_EYECANDY_GRADIENT: old_gradient,
        })
        await self.longer_pause()
        self.take_screenshot('19-main-dark')

        settings.set({
            S.APPLICATION_FOCUS_FLAVOR: 'classic',
            S.APPLICATION_EYECANDY_TYPE: 'default',
            S.APPLICATION_THEME: 'desert',
        })
        await self.longer_pause()
        self.take_screenshot('31-classic-focus-flavor')

        await self._void_pomodoro('Slides for #Flowkeeper demo')
        await self._complete_workitem('Slides for #Flowkeeper demo')

        settings.set({
            S.POMODORO_DEFAULT_WORK_DURATION: old_value_work,
            S.POMODORO_DEFAULT_REST_DURATION: old_value_rest,
            S.APPLICATION_TIMER_UI_MODE: old_value_style,
            S.APPLICATION_THEME: old_value_theme,
            S.APPLICATION_EYECANDY_TYPE: old_eyecandy_type,
            S.APPLICATION_EYECANDY_GRADIENT: old_gradient,
            S.APPLICATION_FOCUS_FLAVOR: old_focus_flavor,
        })
        await self.longer_pause()

        await self._find_workitem('Generate new screenshots for #Flowkeeper')

        backlogs_table._menu.popup(backlogs_table.mapToGlobal(QPoint(100, 300)))
        await self.instant_pause()
        self.take_screenshot('01-backlog')
        backlogs_table._menu.close()

        self.keypress(Qt.Key.Key_F10)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()

        shortcuts_dropdown: QComboBox = self.window().findChild(QComboBox, "Application.shortcuts-list")
        shortcuts_dropdown.setCurrentIndex(11)  # "New item"
        await self.instant_pause()

        workitems_table._menu.popup(workitems_table.mapToGlobal(QPoint(400, 20)))
        await self.instant_pause()
        self.take_screenshot('06-shortcuts')
        workitems_table._menu.close()

        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        # Import -- all, file, CSV, GitHub
        for i in range(3):
            self.keypress(Qt.Key.Key_I, True)
            await self.instant_pause()
            self.center_window()
            await self.instant_pause()
            if i == 0:
                self.take_screenshot('11-import')
            if i == 1:
                self.check_radiobutton(text='Import from CSV')
            elif i == 2:
                self.check_radiobutton(name='Import from GitHub')
            await self.instant_pause()
            self.click_button(name='qt_wizard_commit')
            await self.instant_pause()
            if i == 0:
                self.take_screenshot('23-import-file')
            elif i == 1:
                self.take_screenshot('24-import-CSV')
            elif i == 2:
                self.take_screenshot('25-import-GitHub')
            self.keypress(Qt.Key.Key_Escape)
            await self.instant_pause()

        self.keypress(Qt.Key.Key_E, True)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()
        self.take_screenshot('12-export')
        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        self.keypress(Qt.Key.Key_F3)
        await self.longer_pause()
        self.take_screenshot('16-work-summary')
        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        # Themes
        self.get_application().get_settings().set({
            S.APPLICATION_THEME: 'dark',
            S.APPLICATION_EYECANDY_TYPE: 'default',
        })
        await self.longer_pause()
        self.take_screenshot('08-dark-theme')

        self.get_application().get_settings().set({
            S.APPLICATION_THEME: 'light',
        })
        await self.longer_pause()
        self.take_screenshot('09-light-theme')

        self.get_application().get_settings().set({
            S.APPLICATION_THEME: 'dark',
            S.APPLICATION_EYECANDY_TYPE: 'image',
            S.APPLICATION_EYECANDY_IMAGE: ':/img/bg.jpg',
            # S.APPLICATION_FONT_HEADER_FAMILY: 'Quicksand Light',
            # S.APPLICATION_FONT_HEADER_SIZE: '28',
            # S.APPLICATION_FONT_MAIN_FAMILY: 'Quicksand',
            # S.APPLICATION_FONT_MAIN_SIZE: '10',
            S.APPLICATION_SHOW_TOOLBAR: 'True',
            S.APPLICATION_FULL_SCREEN_NOTIFICATIONS: 'False',
            S.APPLICATION_SHOW_LEFT_TOOLBAR: 'False',
        })
        await self.longer_pause()
        self.keypress(Qt.Key.Key_B, True)
        await self.instant_pause()
        self.window().resize(QSize(400, 400))
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        self.take_screenshot('10-customized')

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

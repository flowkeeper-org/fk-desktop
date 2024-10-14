import asyncio
import datetime
import os
import random

from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtWidgets import QTabWidget, QComboBox, QLineEdit, QCheckBox, QPushButton

from fk.core.abstract_data_item import generate_uid
from fk.core.pomodoro import Pomodoro
from fk.core.pomodoro_strategies import StartWorkStrategy
from fk.core.workitem import Workitem
from fk.desktop.application import Application
from fk.e2e.abstract_e2e_test import AbstractE2eTest, WINDOW_GALLERY_FILENAME, SCREEN_GALLERY_FILENAME
from fk.qt.backlog_tableview import BacklogTableView
from fk.qt.search_completer import SearchBar
from fk.qt.workitem_tableview import WorkitemTableView

TEMP_FILENAME = './screenshots-e2e.txt'
POMODORO_WORK_DURATION = 1  # seconds
POMODORO_REST_DURATION = 1  # seconds


class ScreenshotE2eTest(AbstractE2eTest):
    def __init__(self, app: Application):
        super().__init__(app)

    def setup(self) -> None:
        if os.path.isfile(WINDOW_GALLERY_FILENAME):
            os.unlink(WINDOW_GALLERY_FILENAME)
        if os.path.isfile(SCREEN_GALLERY_FILENAME):
            os.unlink(SCREEN_GALLERY_FILENAME)

    def custom_settings(self) -> dict[str, str]:
        custom = {
            'FileEventSource.filename': TEMP_FILENAME,
            'Application.show_tutorial': 'False',
            'Application.show_window_title': 'True',
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
            'Application.theme': 'mixed',
        }
        if os.name == 'nt':
            custom['Application.font_main_size'] = '10'
            custom['Application.font_header_family'] = 'Segoe UI Light'
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

    async def test_01_screenshots(self):
        main_window = self.window()
        self.center_window()
        await self.instant_pause()

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

        self.keypress(Qt.Key.Key_F10)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        settings_tabs: QTabWidget = self.window().findChild(QTabWidget, "settings_tabs")
        settings_tabs.setCurrentIndex(1)
        await self.instant_pause()
        source_type_dropdown: QComboBox = self.window().findChild(QComboBox, "Source.type")
        source_type_dropdown.setCurrentIndex(0)
        await self.instant_pause()
        data_file_edit: QLineEdit = self.window().findChild(QLineEdit, "FileEventSource.filename-edit")
        data_file_edit.selectAll()
        await self.instant_pause()
        self.take_screenshot('03-settings-connection-offline')

        source_type_dropdown.setCurrentIndex(2)
        await self.instant_pause()
        self.take_screenshot('04-settings-connection-self-hosted')

        source_type_dropdown.setCurrentIndex(1)
        await self.instant_pause()
        auth_type_dropdown: QComboBox = self.window().findChild(QComboBox, "WebsocketEventSource.auth_type")
        auth_type_dropdown.showPopup()
        await self.instant_pause()

        self.take_screenshot('05-settings-connection-flowkeeper-org')

        auth_type_dropdown.hidePopup()
        await self.instant_pause()

        settings_tabs.setCurrentIndex(4)
        await self.instant_pause()
        sound_alarm_check: QCheckBox = self.window().findChild(QCheckBox, "Application.play_alarm_sound")
        sound_alarm_check.setChecked(True)
        await self.instant_pause()
        sound_alarm_check: QCheckBox = self.window().findChild(QCheckBox, "Application.play_rest_sound")
        sound_alarm_check.setChecked(True)
        await self.instant_pause()
        sound_file_edit: QLineEdit = self.window().findChild(QLineEdit, "Application.alarm_sound_file-edit")
        sound_file_edit.selectAll()
        await self.instant_pause()
        self.take_screenshot('07-settings-audio')
        sound_alarm_check.setChecked(False)
        await self.instant_pause()

        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        await self._new_workitem('Generate new screenshots for #Flowkeeper', 2)
        await self._new_workitem('Reply to Peter', 1)
        await self._new_workitem('Slides for #Flowkeeper demo', 3)
        await self._new_workitem('#Flowkeeper: Deprecate StartRest strategy', 2)
        await self._new_workitem('#Flowkeeper: Auto-seal in the web frontend', 2)
        await self._new_workitem('Order coffee capsules')
        await self._new_workitem('#Followup: Call Alex in the afternoon')

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
        await self._wait_mid_pomodoro()
        await self._void_pomodoro()
        await self._complete_workitem()

        await self._find_workitem('Order coffee capsules')
        await self._complete_workitem()

        await self._find_workitem('#Followup: Call Alex in the afternoon')
        await self._complete_workitem()

        await self._find_workitem('Slides for #Flowkeeper demo')
        await self._start_pomodoro()
        await self._wait_mid_pomodoro()
        await self._void_pomodoro()

        # Tags
        await self._select_tag('Flowkeeper')
        await self.instant_pause()
        self.take_screenshot('20-tags')
        await self.instant_pause()
        await self._find_workitem('Slides for #Flowkeeper demo')
        await self.instant_pause()

        # Take two "main" screenshots right in the middle of this pomodoro
        settings = self.get_application().get_settings()
        old_value_work = settings.get('Pomodoro.default_work_duration')
        old_value_rest = settings.get('Pomodoro.default_rest_duration')
        old_value_style = settings.get('Application.timer_ui_mode')
        old_value_theme = settings.get('Application.theme')
        old_gradient = settings.get('Application.eyecandy_gradient')
        settings.set({
            'Pomodoro.default_work_duration': '1500',
            'Pomodoro.default_rest_duration': '300',
            'Application.timer_ui_mode': 'keep',
            'Application.theme': 'light',
            'Application.eyecandy_gradient': 'HiddenJaguar',
        })

        # Start a Pomodoro in the past
        source = self.get_application().get_source_holder().get_source()
        workitem_id = None
        for w in source.workitems():
            if w.get_name() == 'Slides for #Flowkeeper demo':
                workitem_id = w.get_uid()
        source.execute_prepared_strategy(StartWorkStrategy(
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
            'Application.theme': 'dark',
            'Application.eyecandy_gradient': old_gradient,
        })
        await self.longer_pause()
        self.take_screenshot('19-main-dark')

        await self._void_pomodoro()
        await self._complete_workitem()

        settings.set({
            'Pomodoro.default_work_duration': old_value_work,
            'Pomodoro.default_rest_duration': old_value_rest,
            'Application.timer_ui_mode': old_value_style,
            'Application.theme': old_value_theme,
            'Application.eyecandy_gradient': old_gradient,
        })
        await self.longer_pause()

        await self._find_workitem('Generate new screenshots for #Flowkeeper')

        backlogs_table: BacklogTableView = main_window.findChild(BacklogTableView, "backlogs_table")
        backlogs_table._menu.popup(backlogs_table.mapToGlobal(QPoint(100, 400)))
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

        workitems_table: WorkitemTableView = main_window.findChild(WorkitemTableView, "workitems_table")
        workitems_table._menu.popup(workitems_table.mapToGlobal(QPoint(400, 20)))
        await self.instant_pause()
        self.take_screenshot('06-shortcuts')
        workitems_table._menu.close()

        self.keypress(Qt.Key.Key_Escape)
        await self.instant_pause()

        self.keypress(Qt.Key.Key_I, True)
        await self.instant_pause()
        self.center_window()
        await self.instant_pause()
        self.keypress(Qt.Key.Key_Enter)
        await self.instant_pause()
        self.take_screenshot('11-import')
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
            'Application.theme': 'dark',
            'Application.eyecandy_type': 'default',
        })
        await self.longer_pause()
        self.take_screenshot('08-dark-theme')

        self.get_application().get_settings().set({
            'Application.theme': 'light',
        })
        await self.longer_pause()
        self.take_screenshot('09-light-theme')

        self.get_application().get_settings().set({
            'Application.theme': 'resort',
            'Application.eyecandy_type': 'image',
            'Application.eyecandy_image': ':/icons/bg.jpg',
            'Application.font_header_family': 'Impact',
            'Application.font_header_size': '32',
            'Application.show_toolbar': 'False',
        })
        await self.longer_pause()
        self.keypress(Qt.Key.Key_B, True)
        await self.instant_pause()
        self.window().resize(QSize(500, 400))
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
                workitem = Workitem('Huge', uid, b, now)
                b[uid] = workitem
                self._emulate_year(workitem, now - datetime.timedelta(days=365))

    def _emulate_year(self, workitem: Workitem, start_date: datetime.datetime):
        for day in range(365):
            now = start_date + datetime.timedelta(days=day)
            now = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            self._emulate_day(workitem, now, day)

    def _emulate_day(self, workitem: Workitem, start_date: datetime.datetime, day: int):
        weekday = start_date.weekday()
        if weekday < 5 or random.random() < 0.05:
            avg_pomos = 10 + round(day / 100) - weekday
            num_pomos = round(avg_pomos * (1 + (random.random() - 0.5) / 5))
            now = start_date + datetime.timedelta(minutes=round(60 * 7 + random.random() * 180))
            for p in range(num_pomos):
                uid = generate_uid()
                state_selector = random.random()
                if state_selector < 0.1 + (365 - day) / 1200:
                    state = 'canceled'
                elif state_selector < 0.5 + day / 900:
                    state = 'finished'
                else:
                    state = 'new'
                workitem[uid] = Pomodoro(True, state, 25 * 60, 5 * 60, uid, workitem, now)
                now = now + datetime.timedelta(minutes=round(random.random() * 20))

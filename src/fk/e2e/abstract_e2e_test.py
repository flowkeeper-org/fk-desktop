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
from __future__ import annotations

import asyncio
import atexit
import inspect
import logging
import os
import traceback
from abc import ABC
from datetime import datetime
from typing import Callable
from xml.etree import ElementTree

from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QWindow, QMouseEvent, QKeyEvent, QFocusEvent
from PySide6.QtWidgets import QWidget, QAbstractItemView, QMainWindow, QAbstractButton, QCheckBox, QRadioButton

from fk.desktop.application import Application
from fk.e2e.screenshot import Screenshot
from fk.qt.actions import Actions

INSTANT_DURATION = 0.5  # seconds
STARTUP_DURATION = 3  # seconds
WINDOW_GALLERY_FILENAME = 'test-results/screenshots-window.html'
WINDOW_BORDER_GALLERY_FILENAME = 'test-results/screenshots-window-border.html'
FULLSCREEN_GALLERY_FILENAME = 'test-results/screenshots-full.html'

logger = logging.getLogger(__name__)


class AbstractE2eTest(ABC):
    _timer: QTimer
    _seq: list[Callable]
    _app: Application
    _initialized: bool
    _log_filename: str
    _log_xml: ElementTree.Element
    _failures: int
    _errors: int
    _skipped: int
    _tests: int
    _start: datetime
    _current_method: str
    _screenshot: Screenshot
    _main_window: QMainWindow

    def __init__(self, app: Application):
        self._app = app
        self._screenshot = None
        self._main_window = None
        self._current_method = 'N/A'
        app.get_settings().set(self.custom_settings())
        self._initialized = False
        self._seq = self._get_test_cases()
        self._timer = QTimer()
        self._log_xml = None
        self._log_filename = None
        self._timer.timeout.connect(lambda: asyncio.ensure_future(
            self._run()
        ))

    def _get_test_cases(self):
        methods = inspect.getmembers(self.__class__, predicate=inspect.isfunction)
        res = list()
        for m in methods:
            if m[0].startswith('test_'):
                res.append(m[1])
        return res

    async def _run(self):
        self._timer.stop()
        if not self._initialized:
            self._initialized = True
            # noinspection PyTypeChecker
            window: QWindow = self._app.activeWindow()
            if window:
                self._timer.stop()
                self.setup()
                atexit.register(self.teardown)
                self._tests = len(self._seq)
                self._failures = 0
                self._errors = 0
                self._skipped = len(self._seq)
                self._start = datetime.now()
                self.init_log()
                try:
                    for method in self._seq:
                        method_start = datetime.now()
                        try:
                            self._current_method = method.__name__
                            self._update_log_for_method('timestamp', method_start.isoformat())
                            await method(self)
                        except Exception as e:
                            self.error(e)
                        finally:
                            self._skipped -= 1
                            method_duration = (datetime.now() - method_start).total_seconds()
                            if method_duration < 0.0001:
                                method_duration = 0.0001    # Otherwise we'd get scientific notation in output
                            self._update_log_for_method('time', str(method_duration))
                finally:
                    logger.debug(f'*** E2e tests completed {"successfully" if self._errors == 0 and self._skipped == 0 and self._failures == 0 else "with errors" } ***')
                    self.close_log()
                    logger.debug('Do whatever it takes to exit')
                    window.close()
                    logger.debug(' - Closed the window')
                    self._app.exit(0)
                    logger.debug(' - Exited Qt')
                    # sys.exit(0)
                    # logger.debug(' - Exited Python')

    def _update_log_for_method(self, name: str, value: str):
        el = self._log_xml.find(f"testcase[@name='{self._current_method}']")
        el.set(name, value)

    def _append_to_system_out_for_method(self, line: str):
        if self._log_xml is not None:
            el = self._log_xml.find(f"testcase[@name='{self._current_method}']/system-out")
            if el.text:
                el.text += '\n'
            el.text += line

    def init_log(self) -> None:
        filename = f"{__name__.replace('.', '/')}.py"
        test_name = f'{__name__}.{self.__class__.__name__}'
        if not os.path.exists('test-results'):
            os.mkdir('test-results')
        self._log_filename = f'test-results/TEST-{test_name}.xml'
        logger.debug(f'Creating a log file {self._log_filename}')
        self._log_xml = ElementTree.Element('testsuite')
        self._log_xml.set('name', test_name)
        self._log_xml.set('file', filename)
        self._log_xml.set('timestamp', datetime.now().isoformat())
        for method in self._seq:
            testcase = ElementTree.SubElement(self._log_xml, 'testcase', {
                'classname': __name__,
                'name': method.__code__.co_name,
                'file': filename,
                'line': str(method.__code__.co_firstlineno),
            })
            system_out = ElementTree.SubElement(testcase, 'system-out')
            system_out.text = ''

    def close_log(self) -> None:
        if self._log_xml is not None and self._log_filename is not None:
            logger.debug(f'Saving file {self._log_filename}')
            self._log_xml.set('tests', str(self._tests))
            self._log_xml.set('time', str((datetime.now() - self._start).total_seconds()))
            self._log_xml.set('failures', str(self._failures))
            self._log_xml.set('errors', str(self._errors))
            self._log_xml.set('skipped', str(self._skipped))
            tree = ElementTree.ElementTree(self._log_xml)
            ElementTree.indent(tree, space="    ", level=0)
            tree.write(self._log_filename,
                       encoding='utf-8',
                       xml_declaration=True)
            self._log_filename = None
            self._log_xml = None

    def info(self, txt):
        logger.info(f'INFO: {self._current_method}: {txt}')
        self._append_to_system_out_for_method(txt)

    def error(self, e: Exception):
        logger.error(f'ERROR: {self._current_method}', exc_info=e)
        self._append_to_system_out_for_method(f'ERROR: {e}')
        self._errors += 1

    def _get_row_position(self, widget: QAbstractItemView, row: int, col: int) -> QPoint:
        return widget.visualRect(widget.model().index(row, col)).center()

    async def mouse_click_row(self, widget: QAbstractItemView, row: int, col: int = 0):
        logger.debug(f'mouse_click_row({widget.objectName()}, {row}, {col})')
        await self.mouse_click(widget, self._get_row_position(widget, row, col))

    async def mouse_doubleclick_row(self, widget: QAbstractItemView, row: int, col: int = 0):
        logger.debug(f'mouse_doubleclick_row({widget.objectName()}, {row}, {col})')
        await self.mouse_doubleclick(widget, self._get_row_position(widget, row, col))

    async def mouse_click(self, widget: QWidget, pos: QPoint, left_button: bool = True):
        logger.debug(f'mouse_click({widget.objectName()}, {pos}, {left_button})')
        widget.focusInEvent(QFocusEvent(
            QEvent.Type.FocusIn,
        ))
        await self.instant_pause()
        widget.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton if left_button else Qt.MouseButton.RightButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ))
        await self.instant_pause()
        widget.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            pos,
            Qt.MouseButton.LeftButton if left_button else Qt.MouseButton.RightButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ))
        await self.instant_pause()

    async def mouse_doubleclick(self, widget: QWidget, pos: QPoint = QPoint(5, 5)):
        logger.debug(f'mouse_doubleclick({widget.objectName()}, {pos})')
        widget.mouseDoubleClickEvent(QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        ))
        await self.instant_pause()

    def keypress(self, key: int, ctrl: bool = False, widget: QWidget = None):
        logger.debug(f'keypress({key}, {ctrl}, {widget})')
        if widget is None:
            widget = self.get_focused()
        self._app.postEvent(widget, QKeyEvent(
            QEvent.Type.KeyPress,
            key,
            Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
        ))

    def close_modal(self, ok: bool = True):
        logger.debug(f'close_modal({ok})')
        for w in self._app.allWindows():
            if w.isModal():
                if ok:
                    self.keypress(Qt.Key.Key_Enter, False, w)
                else:
                    self.keypress(Qt.Key.Key_Escape, False, w)

    def type_text(self, text: str):
        logger.debug(f'type_text({text})')
        self._app.postEvent(self.get_focused(), QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_No,
            Qt.KeyboardModifier.NoModifier,
            text,
        ))

    def get_focused(self) -> QWidget:
        return self._app.focusWidget()

    def get_application(self) -> Application:
        return self._app

    def window(self) -> QWidget:
        win = self._app.activeWindow()
        if win is None:
            win = self._main_window
            if win is None:
                raise Exception('Cannot find active window')
        else:
            self._main_window = win
        return win

    def click_button(self, text: str = None, name: str = None):
        logger.debug(f'click_button({text}, {name})')
        buttons: list[QAbstractButton] = self.get_application().activeWindow().findChildren(QAbstractButton)
        for b in buttons:
            if text is not None and b.text() == text or name is not None and b.objectName() == name:
                b.click()

    def check_checkbox(self, checked: bool = True, text: str = None, name: str = None):
        logger.debug(f'check_checkbox({checked}, {text}, {name})')
        checkboxes: list[QCheckBox] = self.get_application().activeWindow().findChildren(QCheckBox)
        for c in checkboxes:
            if text is not None and c.text() == text or name is not None and c.objectName() == name:
                c.setChecked(checked)

    def check_radiobutton(self, checked: bool = True, text: str = None, name: str = None):
        logger.debug(f'check_radiobutton({checked}, {text}, {name})')
        radios: list[QRadioButton] = self.get_application().activeWindow().findChildren(QRadioButton)
        for r in radios:
            if text is not None and r.text() == text or name is not None and r.objectName() == name:
                r.setChecked(checked)

    def execute_action(self, name: str) -> None:
        logger.debug(f'execute_action({name})')
        Actions.ALL[name].trigger()

    def is_action_enabled(self, name: str) -> bool:
        return Actions.ALL[name].isVisible() and Actions.ALL[name].isEnabled()

    def custom_settings(self) -> dict[str, str]:
        return dict()

    def start(self) -> None:
        self._timer.start(STARTUP_DURATION * 1000)

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        self.close_log()

    async def instant_pause(self) -> None:
        await asyncio.sleep(INSTANT_DURATION)

    async def longer_pause(self) -> None:
        await self.instant_pause()
        await self.instant_pause()
        await self.instant_pause()
        await self.instant_pause()
        await self.instant_pause()

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        self.info('Exception: ' + to_log)

    def take_screenshot(self, name: str):
        if self._screenshot is None:    # Lazy init, because we don't always want to take screenshots
            self._screenshot = Screenshot()
        self._screenshot.take_window(name, self.window())
        self._screenshot.take_screen(name)

        # Update window gallery
        if not os.path.isfile(WINDOW_GALLERY_FILENAME):
            with open(WINDOW_GALLERY_FILENAME, 'w', encoding='UTF-8') as f:
                f.write('''
                    <style>
                    .screenshot {
                        box-shadow: 5px 5px 30px 0px rgba(0, 0, 0, 0.5);
                        margin: 30px;
                        width: 500px;
                        height: auto;
                    }
                    </style>
                ''')
        with open(WINDOW_GALLERY_FILENAME, 'a', encoding='UTF-8') as f:
            f.write(f'<img class="screenshot" src="{name}-window.png" title="{name}">\n')

        # Update window w/border gallery
        if not os.path.isfile(WINDOW_BORDER_GALLERY_FILENAME):
            with open(WINDOW_BORDER_GALLERY_FILENAME, 'w', encoding='UTF-8') as f:
                f.write('''
                    <style>
                    .screenshot {
                        margin: 30px;
                        width: 500px;
                        height: auto;
                    }
                    </style>
                ''')
        with open(WINDOW_BORDER_GALLERY_FILENAME, 'a', encoding='UTF-8') as f:
            f.write(f'<img class="screenshot" src="{name}-window-border.png" title="{name}">\n')

        # Update screen gallery
        if not os.path.isfile(FULLSCREEN_GALLERY_FILENAME):
            with open(FULLSCREEN_GALLERY_FILENAME, 'w', encoding='UTF-8') as f:
                f.write('''
                    <style>
                    .screenshot {
                        box-shadow: 5px 5px 30px 0px rgba(0, 0, 0, 0.5);
                        margin: 30px;
                        width: 1000px;
                        height: auto;
                    }
                    </style>
                ''')
        with open(FULLSCREEN_GALLERY_FILENAME, 'a', encoding='UTF-8') as f:
            f.write(f'<img class="screenshot" src="{name}-full.png" title="{name}">\n')

    def center_window(self):
        screen_center = self._app.primaryScreen().geometry().center()
        fg = self.window().geometry()
        self.window().move(screen_center - (fg.center() - fg.topLeft()))

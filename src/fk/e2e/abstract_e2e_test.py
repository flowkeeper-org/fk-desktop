import asyncio
import atexit
import inspect
import os
import sys
import traceback
from abc import ABC
from datetime import datetime
from typing import Callable, Self
from xml.etree import ElementTree

from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QWindow, QMouseEvent, QKeyEvent, QFocusEvent
from PySide6.QtWidgets import QApplication, QWidget, QAbstractButton, QAbstractItemView

from fk.desktop.application import Application
from fk.qt.actions import Actions

INSTANT_DURATION = 0.1  # seconds
STARTUP_DURATION = 1  # seconds


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

    def __init__(self, app: Application):
        self._app = app
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
                self._skipped = 0
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
                            method_duration = (datetime.now() - method_start).total_seconds()
                            if method_duration < 0.0001:
                                method_duration = 0.0001    # Otherwise we'd get scientific notation in output
                            self._update_log_for_method('time', str(method_duration))
                finally:
                    self.close_log()
                self._app.exit(0)

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
        print(f'INFO: Creating a log file {self._log_filename}')
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
            print(f'Saving file {self._log_filename}')
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
        print(f'INFO: {self._current_method}: {txt}')
        self._append_to_system_out_for_method(txt)

    def error(self, e: Exception):
        print(f'ERROR: {self._current_method}: {e}')
        self._append_to_system_out_for_method(f'ERROR: {e}')
        self._errors += 1

    def do(self, what: Callable[[], None], delay: int = 1) -> Self:
        self._timer.timeout.disconnect()
        self._timer.timeout.connect(lambda: self._do_once(what))
        self._timer.start(delay)
        return self

    def _do_once(self, what: Callable[[], None]):
        self._timer.stop()
        what()

    def _get_row_position(self, widget: QAbstractItemView, row: int, col: int) -> QPoint:
        row_rect = widget.visualRect(widget.model().index(row, col))
        row_rect.setTop(row_rect.top() + 5)
        row_rect.setLeft(row_rect.left() + 5)
        return row_rect.topLeft()

    def mouse_click_row(self, widget: QAbstractItemView, row: int, col: int = 0):
        self.mouse_click(widget, self._get_row_position(widget, row, col))

    def mouse_doubleclick_row(self, widget: QAbstractItemView, row: int, col: int = 0):
        self.mouse_doubleclick(widget, self._get_row_position(widget, row, col))

    def mouse_click(self, widget: QWidget, pos: QPoint = QPoint(5, 5)):
        self.do(lambda: widget.focusInEvent(QFocusEvent(
            QEvent.Type.FocusIn,
        )))
        self.do(lambda: widget.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )))
        self.do(lambda: widget.mousePressEvent(QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )))

    def mouse_doubleclick(self, widget: QWidget, pos: QPoint = QPoint(5, 5)):
        self.do(lambda: widget.mouseDoubleClickEvent(QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )))

    def button_click(self, button_id: str):
        # noinspection PyTypeChecker
        button: QAbstractButton = self._app.activeWindow().findChild(QAbstractButton, button_id)
        self.do(lambda: button.click())

    def keypress(self, key: int, ctrl: bool = False, widget: QWidget = None):
        if widget is None:
            widget = self.get_focused()
        self._app.postEvent(widget, QKeyEvent(
            QEvent.Type.KeyPress,
            key,
            Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
        ))

    def close_modal(self, ok: bool = True):
        for w in self._app.allWindows():
            if w.isModal():
                if ok:
                    self.keypress(Qt.Key.Key_Tab, False, w)
                self.keypress(Qt.Key.Key_Enter, False, w)

    def type_text(self, text: str):
        self._app.postEvent(self.get_focused(), QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_No,
            Qt.KeyboardModifier.NoModifier,
            text,
        ))

    def get_focused(self) -> QWidget:
        return self._app.focusWidget()

    def get_application(self) -> QApplication:
        return self._app

    def window(self) -> QWidget:
        return self._app.activeWindow()

    def execute_action(self, name: str) -> None:
        Actions.ALL[name].trigger()

    def is_action_enabled(self, name: str) -> bool:
        return Actions.ALL[name].isVisible() and Actions.ALL[name].isEnabled()

    def custom_settings(self) -> dict[str, str]:
        return dict()

    def start(self) -> None:
        self._timer.start(STARTUP_DURATION * 1000)

    def restart(self) -> None:
        # TODO: This needs to be tested
        os.execv(__file__, sys.argv)
        # or
        os.execv(sys.executable, ['python'] + sys.argv)

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        self.close_log()

    async def instant_pause(self) -> None:
        await asyncio.sleep(INSTANT_DURATION)

    def on_exception(self, exc_type, exc_value, exc_trace):
        to_log = "".join(traceback.format_exception(exc_type, exc_value, exc_trace))
        self.info('Exception: ' + to_log)

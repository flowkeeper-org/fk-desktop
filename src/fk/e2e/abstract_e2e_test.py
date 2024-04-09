import asyncio
import atexit
import inspect
import os
import sys
from abc import ABC
from typing import Callable, Self

from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QWindow, QMouseEvent, QKeyEvent, QFocusEvent
from PySide6.QtWidgets import QApplication, QWidget, QAbstractButton, QAbstractItemView

from fk.desktop.application import Application
from fk.qt.actions import Actions


INSTANT_DURATION = 0.01  # seconds
STARTUP_DURATION = 2  # seconds


class AbstractE2eTest(ABC):
    _timer: QTimer
    _seq: list[Callable]
    _app: Application
    _initialized: bool

    def __init__(self, app: Application):
        self._app = app
        app.get_settings().set(self.custom_settings())
        self._initialized = False
        self._seq = self._get_test_cases()
        self._timer = QTimer()
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
                try:
                    self.setup()
                    atexit.register(self.teardown)
                    for method in self._seq:
                        await method(self)
                except Exception as e:
                    print(f'Error (RECORD ME): {e}')

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

    def close_modal(self):
        for w in self._app.allWindows():
            if w.isModal():
                print('Modal', w)

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

    def execute_action(self, name: str):
        Actions.ALL[name].trigger()

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
        pass

    async def instant_pause(self) -> None:
        await asyncio.sleep(INSTANT_DURATION)

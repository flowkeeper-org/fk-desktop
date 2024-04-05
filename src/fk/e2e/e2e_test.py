import asyncio
from typing import Callable, Self

from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QWindow, QMouseEvent, QKeyEvent, QFocusEvent
from PySide6.QtWidgets import QApplication, QWidget, QAbstractButton, QAbstractItemView


class E2eTest:
    _timer: QTimer
    _seq: Callable
    _app: QApplication
    _initialized: bool

    def __init__(self, app: QApplication, seq: Callable[[Self], None]):
        self._seq = seq
        self._app = app
        self._initialized = False
        self._timer = QTimer()
        self._timer.timeout.connect(lambda: asyncio.ensure_future(
            self._run()
        ))
        self._timer.start(1)

    async def _run(self):
        if not self._initialized:
            self._initialized = True
            # noinspection PyTypeChecker
            window: QWindow = self._app.activeWindow()
            if window:
                self._timer.stop()
                try:
                    await self._seq(self)
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

    def keypress(self, key: int, ctrl: bool = False):
        self._app.postEvent(self.window(), QKeyEvent(
            QEvent.Type.KeyPress,
            key,
            Qt.KeyboardModifier.ControlModifier if ctrl else Qt.KeyboardModifier.NoModifier,
        ))

    def get_focused(self):
        w = self._app.focusWidget()
        print('Focus widget', w)
        w = self._app.focusWindow()
        print('Focus window', w)
        w = self._app.focusObject()
        print('Focus object', w)

    def get_application(self) -> QApplication:
        return self._app

    def window(self) -> QWidget:
        return self._app.activeWindow()

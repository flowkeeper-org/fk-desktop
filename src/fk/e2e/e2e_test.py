import asyncio
from typing import Callable, Self

from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QWindow, QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget, QAbstractButton


class E2eTest:
    _timer: QTimer
    _seq: Callable
    _app: QApplication

    def __init__(self, app: QApplication, seq: Callable[[Self], None]):
        self._seq = seq
        self._app = app
        self._timer = QTimer()
        self._timer.timeout.connect(lambda: asyncio.ensure_future(
            self._run()
        ))
        self._timer.start(10)

    async def _run(self):
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

    def mouse_click(self, widget: QWidget, pos: QPoint = QPoint(5, 5)):
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

    def button_click(self, button_id: str):
        button: QAbstractButton = self._app.activeWindow().findChild(QAbstractButton, button_id)
        self.do(lambda: button.click())

    def get_application(self) -> QApplication:
        return self._app

    def window(self) -> QWidget:
        return self._app.activeWindow()

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
from typing import Callable, Tuple

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QMouseEvent, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy


class InfoOverlay(QFrame):
    _timer: QTimer
    _on_close: Callable[[None], None]
    _text: str

    def __init__(self,
                 text: str,
                 absolute_position: QPoint,
                 icon: str = None,
                 duration: int = 3,
                 font_scale: float = 0.8,
                 width: int | None = None,
                 on_close: Callable[[], None] = None,
                 on_prev: Callable[[], None] = None):
        super().__init__()
        self._on_close = on_close
        self._text = text

        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(8, 8, 8, 8)
        top_layout.setSpacing(6)
        main_layout.addLayout(top_layout)

        if icon is not None:
            icon_label = QLabel(self)
            icon_label.setPixmap(QPixmap(icon))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            top_layout.addWidget(icon_label)

        self._timer = QTimer(self)
        if duration > 0:
            self._timer.setInterval(duration * 1000)
            self._timer.timeout.connect(self.close)
            self._timer.start()

        main_label = QLabel(self)
        main_label.setObjectName('overlay_text')
        main_label.setText(text)
        main_label.setWordWrap(True)
        font = main_label.font()
        font.setPointSize(font.pointSize() * font_scale)
        main_label.setFont(font)
        top_layout.addWidget(main_label)
        top_layout.addStretch()

        if on_prev is not None:
            bottom_layout = QHBoxLayout()
            bottom_layout.setContentsMargins(8, 0, 8, 8)
            bottom_layout.setSpacing(2)
            main_layout.addLayout(bottom_layout)
            prev_button = QLabel(self)
            prev_button.setObjectName('prev_button')
            prev_button.setText('&lt; <a href="#">Back</a>')
            prev_button.linkActivated.connect(on_prev)
            prev_button.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            smaller_font = QFont(main_label.font())
            smaller_font.setPointSize(font.pointSize() * 0.8)
            prev_button.setFont(smaller_font)
            bottom_layout.addWidget(prev_button)
            bottom_layout.addStretch()

        if width is not None:
            self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))
            self.setFixedWidth(width)

        self.adjustSize()
        self.move(absolute_position)

    def get_text(self):
        return self._text

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.close()

    def close(self):
        global INFO_OVERLAY_INSTANCE
        if self._timer is not None:
            self._timer.stop()
        super().close()
        if self._on_close is not None:
            self._on_close()
        INFO_OVERLAY_INSTANCE = None


# Without it Qt will destroy the overlay before you can see it
INFO_OVERLAY_INSTANCE: InfoOverlay | None = None
TUTORIAL_STEP: int = 0


def show_info_overlay(text: str,
                      absolute_position: QPoint,
                      icon: str = None,
                      duration: int = 3,
                      on_close: Callable[[None], None] = None):
    global INFO_OVERLAY_INSTANCE
    INFO_OVERLAY_INSTANCE = InfoOverlay(text, absolute_position, icon, duration, 0.8, None, on_close, None)
    INFO_OVERLAY_INSTANCE.show()


def show_tutorial(get_step: Callable[[int], Tuple[str, QPoint, str]], width: int | None = None, first: bool = True):
    global TUTORIAL_STEP
    if first:
        TUTORIAL_STEP = 0
    TUTORIAL_STEP += 1
    res = get_step(TUTORIAL_STEP)

    def on_prev():
        global TUTORIAL_STEP
        TUTORIAL_STEP -= 2  # That's because the onMousePress event also fires at the same time
        show_tutorial(get_step, width, False)

    if res is not None:
        text, pos, icon = res
        if text is not None and pos is not None:
            global INFO_OVERLAY_INSTANCE
            INFO_OVERLAY_INSTANCE = InfoOverlay(text,
                                                pos,
                                                f":/icons/tutorial-{icon}.png",
                                                0,
                                                1,
                                                width,
                                                lambda: show_tutorial(get_step, width, False),
                                                on_prev if TUTORIAL_STEP > 1 else None)
            INFO_OVERLAY_INSTANCE.show()


def show_tutorial_overlay(text: str, pos: QPoint, icon: str, on_close: Callable[[], None] = None, width: int | None = None):
    if text is not None and pos is not None:
        global INFO_OVERLAY_INSTANCE
        if INFO_OVERLAY_INSTANCE is not None:
            if INFO_OVERLAY_INSTANCE.isVisible() and INFO_OVERLAY_INSTANCE.get_text() == text:
                # Don't create duplicates
                return
            INFO_OVERLAY_INSTANCE.close()
        INFO_OVERLAY_INSTANCE = InfoOverlay(text,
                                            pos,
                                            f":/icons/tutorial-{icon}.png",
                                            0,
                                            1,
                                            width,
                                            on_close,
                                            None)
        INFO_OVERLAY_INSTANCE.show()

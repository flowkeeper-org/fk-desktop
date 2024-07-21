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
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy, QWidget, QPushButton


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
                 on_prev: Callable[[], None] = None,
                 on_skip: Callable[[], None] = None,
                 arrow: str = None):
        super().__init__()
        self._on_close = on_close
        self._text = text

        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        if arrow is None:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)
        if arrow == 'up':
            triangle = QLabel(self)
            triangle.setPixmap(QPixmap(':/icons/triangle-up.svg'))
            triangle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(triangle)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._timer = QTimer(self)
        if duration > 0:
            self._timer.setInterval(duration * 1000)
            self._timer.timeout.connect(self.close)
            self._timer.start()

        widget = InfoOverlayContent(self,
                                    text,
                                    icon,
                                    font_scale,
                                    on_prev,
                                    on_skip)
        main_layout.addWidget(widget)

        if arrow == 'down':
            triangle = QLabel(self)
            triangle.setPixmap(QPixmap(':/icons/triangle-down.svg'))
            triangle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(triangle)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if width is not None:
            self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))
            self.setFixedWidth(width)

        self.adjustSize()

        absolute_position.setX(absolute_position.x() - round(self.width() / 2))
        if arrow is None:
            absolute_position.setY(absolute_position.y() - round(self.height() / 2))
        if arrow == 'down':
            absolute_position.setY(absolute_position.y() - self.height())

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
            print('On close', self._on_close)
            self._on_close()
        INFO_OVERLAY_INSTANCE = None


class InfoOverlayContent(QWidget):
    def __init__(self,
                 parent: InfoOverlay,
                 text: str,
                 icon: str = None,
                 font_scale: float = 0.8,
                 on_prev: Callable[[], None] = None,
                 on_skip: Callable[[], None] = None):
        super().__init__()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(6)
        self.setLayout(main_layout)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        main_layout.addLayout(top_layout)

        if icon is not None:
            icon_label = QLabel(self)
            icon_label.setPixmap(QPixmap(icon))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            top_layout.addWidget(icon_label)

        main_label = QLabel(self)
        main_label.setObjectName('overlay_text')
        main_label.setText(text)
        main_label.setWordWrap(True)
        font = main_label.font()
        font.setPointSize(font.pointSize() * font_scale)
        main_label.setFont(font)
        top_layout.addWidget(main_label)
        top_layout.addStretch()

        if on_skip is not None:
            bottom_layout = QHBoxLayout()
            bottom_layout.setContentsMargins(0, 8, 0, 0)
            main_layout.addLayout(bottom_layout)
            skip_button = QPushButton(' Skip tutorial ', self)
            skip_button.setObjectName('skip_button')
            skip_button.clicked.connect(on_skip)
            skip_button.clicked.connect(lambda: parent.close())
            bottom_layout.addStretch()
            bottom_layout.addWidget(skip_button)

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


# Without it Qt will destroy the overlay before you can see it
INFO_OVERLAY_INSTANCE: InfoOverlay | None = None
TUTORIAL_STEP: int = 0


def show_info_overlay(text: str,
                      absolute_position: QPoint,
                      icon: str = None,
                      duration: int = 3,
                      on_close: Callable[[None], None] = None):
    global INFO_OVERLAY_INSTANCE
    INFO_OVERLAY_INSTANCE = InfoOverlay(text,
                                        absolute_position,
                                        icon,
                                        duration,
                                        0.8,
                                        None,
                                        on_close,
                                        None,
                                        None,
                                        None)
    INFO_OVERLAY_INSTANCE.show()


def show_tutorial(get_step: Callable[[int], Tuple[str, QPoint, str]],
                  width: int | None = None,
                  first: bool = True,
                  arrow: str = 'down'):
    global TUTORIAL_STEP
    if first:
        TUTORIAL_STEP = 0
    TUTORIAL_STEP += 1
    res = get_step(TUTORIAL_STEP)

    def on_prev():
        global TUTORIAL_STEP
        TUTORIAL_STEP -= 2  # That's because the onMousePress event also fires at the same time
        show_tutorial(get_step, width, False, arrow)

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
                                                lambda: show_tutorial(get_step, width, False, arrow),
                                                on_prev if TUTORIAL_STEP > 1 else None,
                                                None,
                                                arrow)
            INFO_OVERLAY_INSTANCE.show()


def show_tutorial_overlay(text: str,
                          pos: QPoint,
                          icon: str,
                          on_close: Callable[[], None] = None,
                          on_skip: Callable[[], None] = None,
                          arrow: str = 'down'):
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
                                            None,
                                            on_close,
                                            None,
                                            on_skip,
                                            arrow)
        INFO_OVERLAY_INSTANCE.show()

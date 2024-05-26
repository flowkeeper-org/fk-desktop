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

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class InfoOverlay(QFrame):
    _timer: QTimer

    def __init__(self,
                 text: str,
                 absolute_position: QPoint,
                 icon: str = None,
                 duration: int = 3):
        super().__init__()

        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.setLayout(layout)

        if icon is not None:
            icon_label = QLabel(self)
            icon_label.setPixmap(QPixmap(icon))
            layout.addWidget(icon_label)

        self._timer = QTimer(self)
        if duration > 0:
            self._timer.setInterval(duration * 1000)
            self._timer.timeout.connect(self.close)
            self._timer.start()

        main_label = QLabel(self)
        main_label.setObjectName('overlay_text')
        main_label.setText(text)
        font = main_label.font()
        font.setPointSize(font.pointSize() * 0.8)
        main_label.setFont(font)
        layout.addWidget(main_label)

        self.adjustSize()
        self.move(absolute_position)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.close()

    def close(self):
        if self._timer is not None:
            self._timer.stop()
        # TODO: Save its state in settings
        super().close()


# Without it Qt will destroy the overlay before you can see it
INFO_OVERLAY_INSTANCE: InfoOverlay | None = None


def show_info_overlay(text: str,
                      absolute_position: QPoint,
                      icon: str = None,
                      duration: int = 3):
    global INFO_OVERLAY_INSTANCE
    INFO_OVERLAY_INSTANCE = InfoOverlay(text, absolute_position, icon, duration)
    INFO_OVERLAY_INSTANCE.show()

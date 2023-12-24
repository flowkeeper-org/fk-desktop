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

import datetime
import sys

from PySide6 import QtWidgets, QtUiTools, QtCore, QtGui

from fk.qt.timer_widget import render_for_widget, render_for_pixmap, TimerWidget


def update(timer_widget: TimerWidget, timer_tray: TimerWidget):
    now = datetime.datetime.now()
    v1 = 1 - (now.second + (now.microsecond / 1000000)) / 60.0

    # Update widget
    timer_widget.set_values(
        v1,
        1 - (now.minute + now.second / 60) / 60.0,
        str(round(v1 * 60))
    )
    w.repaint()

    # Update tray
    timer_tray.set_values(
        v1,
        None,
        ""
    )
    tray_width = 48
    tray_height = 48
    pixmap = QtGui.QPixmap(tray_width, tray_height)
    pixmap.fill(QtGui.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    timer_tray.repaint(painter, QtCore.QRect(0, 0, tray_width, tray_height))
    tray.setIcon(pixmap)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    loader = QtUiTools.QUiLoader()
    file = QtCore.QFile(":/timer.ui")
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    w = loader.load(file, None)
    file.close()

    # Create tray icon
    tray_icon = QtGui.QIcon(":/img/icon.png")
    tray = QtWidgets.QSystemTrayIcon()
    tray.setIcon(tray_icon)
    tray.setVisible(True)

    t_widget = render_for_widget(
        app.palette(),
        w,
        QtGui.QFont(),
        0.35
    )

    t_tray = render_for_pixmap()

    qt_timer = QtCore.QTimer()
    qt_timer.timeout.connect(lambda: update(t_widget, t_tray))
    qt_timer.start(99)

    sys.exit(app.exec())

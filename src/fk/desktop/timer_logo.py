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

import sys

from PySide6 import QtWidgets, QtUiTools, QtCore, QtGui

from fk.core.path_resolver import resolve_path
from fk.qt.timer_widget import render_for_logo

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    loader = QtUiTools.QUiLoader()
    file = QtCore.QFile(resolve_path("src/fk/desktop/timer.ui"))
    file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
    w = loader.load(file, None)
    file.close()

    # Create tray icon
    tray_icon = QtGui.QIcon(resolve_path("res/img/red2.png"))
    tray = QtWidgets.QSystemTrayIcon()
    tray.setIcon(tray_icon)
    tray.setVisible(True)

    t_widget = render_for_logo(
        w,
        0.5
    )

    # Update widget
    t_widget.set_values(
        0.6666,
        0.3333,
    )
    t_widget.set_values(
        0.95,
        0.05,
    )
    w.repaint()

    sys.exit(app.exec())

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
from typing import Self

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QWidget


class AddItem(QStandardItem):
    _name: str

    def __init__(self, name: str, parent: QWidget):
        super().__init__()
        self._name = name
        self.setData(None, 500)
        self.setData(f"Click here to create new {name}", Qt.ItemDataRole.ToolTipRole)
        self.setData('additem', 501)
        self.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
        self.setData(f'New {name}', Qt.DisplayRole)
        self.setForeground(parent.palette().link().color())

    def __lt__(self, other: Self):
        return False

    def get_name(self):
        return self._name

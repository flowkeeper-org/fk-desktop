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
from typing import Callable

from PySide6.QtCore import QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QApplication, QTabWidget, QWidget, QGridLayout, QDialog, QFormLayout, QLineEdit, \
    QSpinBox, QCheckBox, QFrame, QHBoxLayout, QPushButton, QComboBox, QDialogButtonBox, QFileDialog

from fk.core.abstract_settings import AbstractSettings
from fk.qt.qt_settings import QtSettings


class SettingsDialog(QDialog):
    _data: AbstractSettings
    _widgets: dict[str, Callable[[], str]]
    _buttons: QDialogButtonBox

    def __init__(self, data: AbstractSettings):
        super().__init__()
        self._data = data
        self._widgets = dict()
        self.resize(QSize(400, 400))
        self.setWindowTitle("Settings")

        buttons = QDialogButtonBox(self)
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Discard |
            QDialogButtonBox.StandardButton.Save
        )
        buttons.clicked.connect(lambda btn: self._on_action(buttons.buttonRole(btn)))
        self._buttons = buttons

        tabs = QTabWidget(self)
        for tab_name in data.get_categories():
            tab = self._create_tab(tabs, data.get_settings(tab_name))
            tabs.addTab(tab, tab_name)

        location = QLabel(self)
        location.setWordWrap(True)
        small_font = QFont()
        small_font.setPointSize(8)
        location.setFont(small_font)
        location.setText(f'Settings saved in {data.location()}')

        root_layout = QGridLayout(self)
        root_layout.addWidget(tabs, 0, 0)
        root_layout.addWidget(location, 1, 0)
        root_layout.addWidget(buttons, 2, 0)
        self.setLayout(root_layout)
        self._set_buttons_state(False)

    def _on_action(self, role: QDialogButtonBox.ButtonRole):
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self._save_settings()
        elif role == QDialogButtonBox.ButtonRole.DestructiveRole:
            self.close()
        elif role == QDialogButtonBox.ButtonRole.AcceptRole:
            self._save_settings()
            self.close()

    def _enable_save_buttons(self, option_id, new_value):
        # print(f"Changed {option_id} to {new_value}")
        # print(f"From {self._data.get(option_id)} to {new_value}")
        self._set_buttons_state(self._data.get(option_id) != new_value)

    def _set_buttons_state(self, is_enabled: bool):
        self._buttons.button(QDialogButtonBox.StandardButton.Apply).setEnabled(is_enabled)
        self._buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(is_enabled)

    def _save_settings(self):
        for name in self._widgets:
            value = self._widgets[name]()
            if self._data.get(name) != value:
                self._data.set(name, value)
        self._set_buttons_state(False)

    @staticmethod
    def _do_browse(edit: QLineEdit) -> None:
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        dlg.selectFile(edit.text())
        if dlg.exec_():
            selected: str = dlg.selectedFiles()[0]
            edit.setText(selected)

    def _display_option(self,
                        parent,
                        option_id: str,
                        option_type: str,
                        option_value: str,
                        option_options) -> list[QWidget]:
        if option_type == 'email' or option_type == 'str':
            ed1 = QLineEdit(parent)
            ed1.setText(option_value)
            ed1.textChanged.connect(lambda v: self._enable_save_buttons(option_id, v))
            self._widgets[option_id] = ed1.text
            return [ed1]
        elif option_type == 'secret':
            ed2 = QLineEdit(parent)
            ed2.setEchoMode(QLineEdit.EchoMode.Password)
            ed2.setText(option_value)
            ed2.textChanged.connect(lambda v: self._enable_save_buttons(option_id, v))
            self._widgets[option_id] = ed2.text
            return [ed2]
        elif option_type == 'file':
            widget = QWidget(parent)
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            ed3 = QLineEdit(parent)
            ed3.setText(option_value)
            ed3.textChanged.connect(lambda v: self._enable_save_buttons(option_id, v))
            self._widgets[option_id] = ed3.text
            layout.addWidget(ed3)
            btn = QPushButton(parent)
            btn.setText('Browse...')
            btn.clicked.connect(lambda: SettingsDialog._do_browse(ed3))
            layout.addWidget(btn)
            return [widget]
        elif option_type == 'int':
            ed4 = QSpinBox(parent)
            ed4.setMinimum(option_options[0])
            ed4.setMaximum(option_options[1])
            ed4.setValue(int(option_value))
            ed4.valueChanged.connect(lambda v: self._enable_save_buttons(option_id, str(v)))
            self._widgets[option_id] = lambda: str(ed4.value())
            return [ed4]
        elif option_type == 'bool':
            ed5 = QCheckBox(parent)
            ed5.setChecked(option_value == 'True')
            ed5.stateChanged.connect(lambda v: self._enable_save_buttons(option_id, str(v == 2)))
            self._widgets[option_id] = lambda: str(ed5.isChecked())
            return [ed5]
        elif option_type == 'choice':
            ed6 = QComboBox(parent)
            ed6.addItems([v.split(':')[1] for v in option_options])
            ed6.currentIndexChanged.connect(lambda v: self._enable_save_buttons(
                option_id,
                option_options[ed6.currentIndex()].split(':')[0]
            ))
            i = 0
            for v in option_options:
                if v.split(':')[0] == option_value:
                    break
                i += 1
            ed6.setCurrentIndex(i)
            self._widgets[option_id] = lambda: option_options[ed6.currentIndex()].split(':')[0]
            return [ed6]
        else:
            return []

    def _create_tab(self, tabs, settings) -> QWidget:
        res = QWidget(tabs)
        layout = QFormLayout(res)
        res.setLayout(layout)

        for option_id, option_type, option_display, option_value, option_options in settings:
            widgets = self._display_option(res, option_id, option_type, option_value, option_options)
            label = QLabel(option_display, res)
            if len(widgets) == 0:
                # Separator
                separator = QFrame(res)
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                separator.setFixedHeight(10)
                layout.addRow(separator)
                pass
            elif len(widgets) == 1:
                widgets[0].setObjectName(f'{option_id}')
                layout.addRow(label, widgets[0])
            else:
                i = 1
                for widget in widgets:
                    widget.setObjectName(f'#{option_id}-{i}')
                    if i == 1:
                        layout.addRow(label, widget)
                    else:
                        layout.addRow(widget)
                    i += 1

        return res


if __name__ == '__main__':
    # Simple tests
    app = QApplication([])
    window = SettingsDialog(QtSettings())
    window.show()
    sys.exit(app.exec())

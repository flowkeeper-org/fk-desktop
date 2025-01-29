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
import json
import logging
import sys
from typing import Callable

from PySide6.QtCore import QSize, QTime, Qt
from PySide6.QtGui import QFont, QKeySequence, QIcon
from PySide6.QtWidgets import QLabel, QApplication, QTabWidget, QWidget, QGridLayout, QDialog, QFormLayout, QLineEdit, \
    QSpinBox, QCheckBox, QFrame, QHBoxLayout, QPushButton, QComboBox, QDialogButtonBox, QFileDialog, QFontComboBox, \
    QMessageBox, QVBoxLayout, QKeySequenceEdit, QTimeEdit, QTableWidget, QTableWidgetItem

from fk.core.abstract_settings import AbstractSettings
from fk.core.sandbox import get_sandbox_type
from fk.qt.actions import Actions
from fk.qt.qt_settings import QtSettings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    _data: AbstractSettings
    _widgets_get_value: dict[str, Callable[[], str]]
    _widgets_set_value: dict[str, Callable[[str], None]]
    _widgets_visibility: dict[QWidget, Callable[[dict[str, str]], bool]]
    _buttons: QDialogButtonBox
    _buttons_mapping: dict[str, Callable[[dict[str, str], Callable], bool]] | None

    def __init__(self,
                 parent: QWidget,
                 data: AbstractSettings,
                 buttons_mapping: dict[str, Callable[[dict[str, str], Callable], bool]] | None = None):
        super().__init__(parent)
        self._data = data
        self._buttons_mapping = buttons_mapping
        self._widgets_get_value = dict()
        self._widgets_set_value = dict()
        self._widgets_visibility = dict()
        self.resize(QSize(500, 450))
        self.setWindowTitle("Settings")

        self._init_sign_out_button()

        buttons = QDialogButtonBox(self)
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.Close |
            QDialogButtonBox.StandardButton.Reset |
            QDialogButtonBox.StandardButton.Save
        )
        buttons.clicked.connect(lambda btn: self._on_action(buttons.buttonRole(btn)))
        self._buttons = buttons

        tabs = QTabWidget(self)
        tabs.setObjectName('settings_tabs')
        for tab_name in data.get_categories():
            tab = self._create_tab(tabs, data.get_settings(tab_name))
            tabs.addTab(tab, tab_name)

        self._recompute_visibility('', '')

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

        # Reinitialize audio outputs -- the sound devices might have changed while Flowkeeper was running
        self._data.init_audio_outputs()

    def _init_sign_out_button(self):
        lst = self._data._definitions['Connection']
        for i, d in enumerate(lst):
            if d[0] == 'WebsocketEventSource.logout':
                t = list(d)
                t[2] = f'Sign out <{self._data.get_username()}>'
                lst[i] = tuple(t)
                return

    def _on_action(self, role: QDialogButtonBox.ButtonRole):
        if role == QDialogButtonBox.ButtonRole.ApplyRole:
            self._save_settings()
        elif role == QDialogButtonBox.ButtonRole.RejectRole:
            self.close()
        elif role == QDialogButtonBox.ButtonRole.ResetRole:
            if QMessageBox().warning(self,
                                     "Confirmation",
                                     f"Are you sure you want to reset settings to their default values, "
                                     f"including data source connection?",
                                     QMessageBox.StandardButton.Ok,
                                     QMessageBox.StandardButton.Cancel
                                     ) == QMessageBox.StandardButton.Ok:
                self._data.reset_to_defaults()
                self.close()
        elif role == QDialogButtonBox.ButtonRole.AcceptRole:
            if self._save_settings():
                self.close()

    def _computed_values(self) -> dict[str, str]:
        computed = dict[str, str]()
        for name in self._widgets_get_value:
            computed[name] = self._widgets_get_value[name]()
        return computed

    def _on_value_changed(self, option_id, new_value):
        changed = False
        logger.debug(f"Changed {option_id} to {new_value}")

        # Enable / disable "save" buttons
        for name in self._widgets_get_value:
            old_value = self._data.get(name)
            calculated_value = new_value if name == option_id else self._widgets_get_value[name]()
            if old_value != calculated_value:
                changed = True
                break

        self._set_buttons_state(changed)
        self._recompute_visibility(option_id, new_value)

    def _recompute_visibility(self, option_id, new_value):
        # Name / value pair here is a hack to "override" settings value for visibility checks
        # because Qt sends value change events BEFORE setValue() finished
        computed = self._computed_values()
        computed[option_id] = new_value
        for widget in self._widgets_visibility:
            is_visible = self._widgets_visibility[widget](computed)
            widget.setVisible(is_visible)

    def _set_buttons_state(self, is_enabled: bool):
        self._buttons.button(QDialogButtonBox.StandardButton.Apply).setEnabled(is_enabled)
        self._buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(is_enabled)

    def _save_settings(self) -> bool:
        # Returns True if the settings were changed
        to_set = dict[str, str]()
        for name in self._widgets_get_value:
            value = self._widgets_get_value[name]()
            if self._data.get(name) != value:
                if self._data.get_type(name) == 'key':
                    if not SettingsDialog.display_key_warning(self._data.get_display_name(name)):
                        return False
                to_set[name] = value
        self._data.set(to_set)
        self._set_buttons_state(False)
        return True

    @staticmethod
    def do_browse(edit: QLineEdit) -> None:
        SettingsDialog.do_browse_simple(edit.text(), edit.setText)

    @staticmethod
    def do_browse_simple(preselected: str, callback: Callable[[str], None]) -> None:
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        dlg.selectFile(preselected)
        if dlg.exec_():
            selected: str = dlg.selectedFiles()[0]
            callback(selected)

    @staticmethod
    def display_key_warning(name: str) -> bool:
        warning_text = f"WARNING: You are about to change the {name}! Read this carefully.\n\n" \
                       \
                       "It is only stored on your computer, so if you lose this key, you won't be able to " \
                       "restore it. Therefore, please SAVE A COPY IN A SAFE PLACE.\n\n" \
                       \
                       "DO NOT CHANGE THIS KEY IF YOU ALREADY CREATED SOME DATA! If you do it, " \
                       "Flowkeeper won't be able to decrypt your old data and so you will lose " \
                       "access to it. Instead, export your data, and then " \
                       "import it into a clean data store with the new key.\n\n" \
                       \
                       "Finally, you will have to provide the same key in all your Flowkeeper apps, which " \
                       "connect to this account."
        return QMessageBox().warning(None,
                                     f"Change {name}?",
                                     warning_text,
                                     QMessageBox.StandardButton.Yes,
                                     QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes

    def _display_option(self,
                        parent: QWidget,
                        option_id: str,
                        option_type: str,
                        option_value: str,
                        option_options: list[any],
                        option_display: str) -> list[QWidget]:
        if option_type == 'email' or option_type == 'str':
            ed1 = QLineEdit(parent)
            ed1.setText(option_value)
            ed1.textChanged.connect(lambda v: self._on_value_changed(option_id, v))
            self._widgets_get_value[option_id] = ed1.text
            self._widgets_set_value[option_id] = ed1.setText
            return [ed1]
        elif option_type == 'secret':
            ed2 = QLineEdit(parent)
            ed2.setEchoMode(QLineEdit.EchoMode.Password)
            ed2.setText(option_value)
            ed2.textChanged.connect(lambda v: self._on_value_changed(option_id, v))
            self._widgets_get_value[option_id] = ed2.text
            self._widgets_set_value[option_id] = ed2.setText
            return [ed2]
        elif option_type == 'file':
            widget = QWidget(parent)
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            ed3 = QLineEdit(parent)
            ed3.setObjectName(f'{option_id}-edit')
            ed3.setText(option_value)
            ed3.textChanged.connect(lambda v: self._on_value_changed(option_id, v))
            self._widgets_get_value[option_id] = ed3.text
            self._widgets_set_value[option_id] = ed3.setText
            if get_sandbox_type() is not None:
                # Force the user to use the XDG portal-aware file chooser
                ed3.setDisabled(True)
            layout.addWidget(ed3)
            browse_btn = QPushButton(parent)
            browse_btn.setObjectName(f'{option_id}-button')
            browse_btn.setText('Browse...')
            browse_btn.clicked.connect(lambda: SettingsDialog.do_browse(ed3))
            layout.addWidget(browse_btn)
            return [widget]
        elif option_type == 'button':
            button = QPushButton(parent)
            button.setText(option_display)
            if len(option_options) > 0:
                button.setIcon(QIcon(f':/icons/{option_options[0]}.png'))
            button.clicked.connect(lambda: self._handle_button_click(option_id))
            self._widgets_get_value[option_id] = lambda: ""
            self._widgets_set_value[option_id] = lambda txt: button.setText(txt)
            return [button]
        elif option_type == 'int':
            ed4 = QSpinBox(parent)
            ed4.setMinimum(option_options[0])
            ed4.setMaximum(option_options[1])
            ed4.setValue(int(option_value))
            ed4.valueChanged.connect(lambda v: self._on_value_changed(option_id, str(v)))
            self._widgets_get_value[option_id] = lambda: str(ed4.value())
            self._widgets_set_value[option_id] = lambda txt: ed4.setValue(int(txt))
            return [ed4]
        elif option_type == 'bool':
            ed5 = QCheckBox(parent)
            ed5.setChecked(option_value == 'True')
            ed5.stateChanged.connect(lambda v: self._on_value_changed(option_id, str(v == 2)))
            self._widgets_get_value[option_id] = lambda: str(ed5.isChecked())
            self._widgets_set_value[option_id] = lambda txt: ed5.setChecked(txt == 'True')
            return [ed5]
        elif option_type == 'choice':
            ed6 = QComboBox(parent)
            ed6.addItems([v.split(':')[1] for v in option_options])
            ed6.setCurrentIndex(self._find_combobox_option(option_options, option_value))
            ed6.currentIndexChanged.connect(lambda v: self._on_value_changed(
                option_id,
                option_options[ed6.currentIndex()].split(':')[0]
            ))
            self._widgets_get_value[option_id] = lambda: option_options[ed6.currentIndex()].split(':')[0]
            self._widgets_set_value[option_id] = lambda txt: ed6.setCurrentIndex(self._find_combobox_option(option_options, txt))
            return [ed6]
        elif option_type == 'font':
            ed7 = QFontComboBox(parent)
            ed7.currentFontChanged.connect(lambda v: self._on_value_changed(
                option_id,
                v.family()
            ))
            ed7.setCurrentFont(option_value)
            self._widgets_get_value[option_id] = lambda: ed7.currentFont().family()
            self._widgets_set_value[option_id] = lambda txt: ed7.currentFont().setFamily(txt)
            return [ed7]
        elif option_type == 'shortcuts':
            widget = QWidget(parent)
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            actions = list(Actions.ALL.keys())
            shortcuts = dict()
            # There's no need to do something like "shortcuts = json.loads(option_value)"
            # as those have been already initialized from the settings on startup
            for a in actions:
                shortcuts[a] = Actions.ALL[a].shortcut().toString()
            seq_edit = QKeySequenceEdit(parent)
            seq_edit.setObjectName(f'{option_id}-edit')
            seq_edit.setKeySequence(shortcuts[actions[0]])
            reset_button = QPushButton(widget)
            reset_button.setObjectName(f'{option_id}-button')
            reset_button.setText('Clear')
            reset_button.clicked.connect(lambda: seq_edit.clear())

            def on_shortcut_changed(k: QKeySequence):
                shortcuts[actions[ed8.currentIndex()]] = k.toString()
                self._on_value_changed(option_id, json.dumps(shortcuts))

            seq_edit.keySequenceChanged.connect(on_shortcut_changed)

            ed8 = QComboBox(parent)
            ed8.setObjectName(f'{option_id}-list')
            ed8.addItems([f'{Actions.ALL[a].text()}' for a in actions])
            ed8.currentIndexChanged.connect(lambda v: seq_edit.setKeySequence(shortcuts[actions[ed8.currentIndex()]]))
            self._widgets_get_value[option_id] = lambda: json.dumps(shortcuts)
            self._widgets_set_value[option_id] = lambda txt: logger.error('Changing shortcuts programmatically is not implemented yet')

            layout.addWidget(ed8)

            hwidget = QWidget(widget)
            hlayout = QHBoxLayout(hwidget)
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.addWidget(seq_edit)
            hlayout.addWidget(reset_button)

            layout.addWidget(hwidget)
            return [widget]
        elif option_type == 'duration':
            ed9 = QTimeEdit(parent)
            ed9.setDisplayFormat('HH:mm:ss')
            ed9.setCurrentSection(QTimeEdit.Section.SecondSection)
            ed9.userTimeChanged.connect(lambda v: self._on_value_changed(
                option_id,
                str(int(v.msecsSinceStartOfDay() / 1000))
            ))
            total_seconds = int(float(option_value))
            hours = int(total_seconds / 60 / 60)
            minutes = int(total_seconds / 60) - hours * 60
            seconds = total_seconds - hours * 60 * 60 - minutes * 60
            ed9.setTime(QTime(hours, minutes, seconds, 0))
            self._widgets_get_value[option_id] = lambda: str(int(ed9.time().msecsSinceStartOfDay() / 1000))
            self._widgets_set_value[option_id] = lambda txt: logger.error('Changing durations programmatically is not implemented yet')
            return [ed9]
        elif option_type == 'key':
            widget = QWidget(parent)
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            ed10 = QLineEdit(parent)
            ed10.setObjectName(f'{option_id}-edit')
            ed10.setText(option_value)
            ed10.setEchoMode(QLineEdit.EchoMode.Password)

            ed10.textChanged.connect(lambda v: self._on_value_changed(option_id, v))
            self._widgets_get_value[option_id] = ed10.text
            self._widgets_set_value[option_id] = ed10.setText

            option_id_cache = f'{option_id.replace("!", "")}_cache!' if option_id.endswith('!') else f'{option_id}_cache'
            ed10.textChanged.connect(lambda v: self._on_value_changed(option_id_cache, v))
            self._widgets_get_value[option_id_cache] = lambda: ''   # Always empty the cache
            layout.addWidget(ed10)

            key_view = QPushButton(parent)
            key_view.setObjectName(f'{option_id}-button')
            key_view.setText('Show')
            key_view.clicked.connect(lambda: ed10.setEchoMode(QLineEdit.EchoMode.Password if ed10.echoMode() == QLineEdit.EchoMode.Normal else QLineEdit.EchoMode.Normal))
            key_view.clicked.connect(lambda: key_view.setText("Show" if key_view.text() == "Hide" else "Hide"))
            layout.addWidget(key_view)
            return [widget]
        elif option_type == 'label':
            ed11 = QLabel(parent)
            ed11.setWordWrap(True)
            ed11.setText(option_value)
            return [ed11]
        elif option_type == 'keyvalue':
            ed13 = QTableWidget(parent)
            ed13.setColumnCount(2)
            ed13.horizontalHeader().setVisible(True)
            ed13.horizontalHeader().setStretchLastSection(True)
            ed13.setHorizontalHeaderItem(0, QTableWidgetItem('Event'))
            ed13.setHorizontalHeaderItem(1, QTableWidgetItem('Command'))
            ed13.verticalHeader().setVisible(False)
            ed13.setRowCount(len(option_options))
            json_value: dict[str, str] = json.loads(option_value)

            flags = (Qt.ItemFlag.ItemIsSelectable |
                     Qt.ItemFlag.ItemIsEnabled)
            for i, option in enumerate(sorted(option_options)):
                item1 = QTableWidgetItem(option)
                item1.setFlags(flags)
                ed13.setItem(i, 0, item1)
                item2 = QTableWidgetItem(json_value[option] if option in json_value else '')
                item2.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                ed13.setItem(i, 1, item2)
            ed13.resizeColumnsToContents()

            def get_value() -> str:
                obj: dict[str, str] = dict()
                for j in range(ed13.rowCount()):
                    key = ed13.item(j, 0).text()
                    value = ed13.item(j, 1).text().strip()
                    if value != '':
                        obj[key] = value
                return json.dumps(obj)

            def set_value(value: str) -> None:
                obj: dict[str, str] = json.loads(value)
                for j in range(ed13.rowCount()):
                    key = ed13.item(j, 0).text()
                    if key in obj:
                        ed13.item(j, 1).setText(obj[key])

            ed13.itemChanged.connect(lambda: self._on_value_changed(option_id, get_value()))
            self._widgets_get_value[option_id] = get_value
            self._widgets_set_value[option_id] = set_value

            return [ed13]
        else:
            return []

    def _find_combobox_option(self, option_options: list[str], option_value: str):
        i = 0
        for v in option_options:
            if v.split(':')[0] == option_value:
                break
            i += 1
        return i

    def _handle_button_click(self, option_id: str):
        if self._buttons_mapping is None or option_id not in self._buttons_mapping:
            QMessageBox().warning(self,
                                  "Not available",
                                  "This button doesn't do anything",
                                  QMessageBox.StandardButton.Close)
            return

        values: dict[str, str] = dict()
        for name in self._widgets_get_value:
            values[name] = self._widgets_get_value[name]()

        if self._buttons_mapping[option_id](values, self._value_changed_extrnally):
            self.close()

    def _value_changed_extrnally(self, name: str, value: str):
        logger.debug(f'Update the setting display of {name} to {value}')
        self._widgets_set_value[name](value)

    def _create_tab(self, tabs: QTabWidget, settings) -> QWidget:
        res = QWidget(tabs)
        layout = QFormLayout(res)

        for option_id, option_type, option_display, option_value, option_options, option_visible in settings:
            widgets = self._display_option(res, option_id, option_type, option_value, option_options, option_display)
            if option_display == '':
                label = None
            else:
                label = QLabel('' if option_type == 'button' else option_display, res)
                label.setObjectName(f'label-{option_id}')
                self._widgets_visibility[label] = option_visible
            if len(widgets) == 0:
                # Separator
                separator = QFrame(res)
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                separator.setFixedHeight(10)
                self._widgets_visibility[separator] = option_visible
                layout.addRow(separator)
                pass
            elif len(widgets) == 1:
                widgets[0].setObjectName(f'{option_id}')
                self._widgets_visibility[widgets[0]] = option_visible
                if label is None:
                    layout.addRow(widgets[0])
                else:
                    layout.addRow(label, widgets[0])
            else:
                i = 1
                for widget in widgets:
                    widget.setObjectName(f'#{option_id}-{i}')
                    self._widgets_visibility[widget] = option_visible
                    if i == 1 and label is not None:
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

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

from PySide6 import QtCore, QtWidgets, QtUiTools

from fk.core.abstract_settings import AbstractSettings
from fk.core.path_resolver import resolve_path


class FileEventSourceSettingsUi:
    _settings: AbstractSettings
    _filename: QtWidgets.QLineEdit

    def __init__(self, settings: AbstractSettings):
        self._settings = settings

    def do_browse(self) -> None:
        dlg = QtWidgets.QFileDialog()
        dlg.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)
        dlg.selectFile(self._settings.get("FileEventSource.filename"))
        if dlg.exec_():
            selected: str = dlg.selectedFiles()[0]
            self._settings.set("FileEventSource.filename", selected)
            self._filename.setText(selected)

    def warning(self) -> None:
        # TODO: This is not strictly necessary if we find a way to refresh everything
        # Think about doing it through DataModels and events
        QtWidgets.QMessageBox().warning(
                self._filename.parent(),
                "Warning",
                f"Please restart Flowkeeper to apply this change",
                QtWidgets.QMessageBox.StandardButton.Ok
        )

    def render_config_ui(self, parent: QtWidgets.QWidget) -> None:
        loader = QtUiTools.QUiLoader()
        file = QtCore.QFile(resolve_path("src/fk/desktop/file-source-settings-ui.ui"))
        file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
        # noinspection PyTypeChecker
        window: QtWidgets.QMainWindow = loader.load(file, parent)
        file.close()

        # noinspection PyTypeChecker
        self._filename: QtWidgets.QLineEdit = window.findChild(QtWidgets.QLineEdit, "filename")
        self._filename.setText(self._settings.get("FileEventSource.filename"))
        self._filename.textChanged.connect(lambda: self.warning())

        # noinspection PyTypeChecker
        browse: QtWidgets.QToolButton = window.findChild(QtWidgets.QToolButton, "browse")
        browse.clicked.connect(lambda: self.do_browse())

        # noinspection PyTypeChecker
        watch_changes: QtWidgets.QCheckBox = window.findChild(QtWidgets.QCheckBox, "watchChanges")
        watch_changes.setCheckState(
            QtCore.Qt.CheckState.Checked
            if self._settings.get("FileEventSource.watch_changes") == 'True' else
            QtCore.Qt.CheckState.Unchecked)

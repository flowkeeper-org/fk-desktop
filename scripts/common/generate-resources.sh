#!/usr/bin/env bash

#
# Flowkeeper - Pomodoro timer for power users and teams
# Copyright (c) 2023 Constantine Kulak
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source ../../venv/bin/activate

set -e

if [[ "$OSTYPE" == "msys" ]]; then
  alias "pyside6-rcc=$(pwd)/venv/Lib/site-packages/PySide6/rcc"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Running macOS create-icons.sh from: $(pwd)"
  echo "Attempting to run: scripts/macos/create-icons.sh"
  "$DIR/../macos/create-icons.sh"
  echo "Generated icns file for macOS"
  ls -al
fi


cd ../../res
qrc="resources.qrc"
pyside6-rcc --project -o "$qrc"
pyside6-rcc -g python "$qrc" -o "../src/fk/desktop/resources.py"
rm "$qrc"
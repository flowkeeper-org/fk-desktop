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

source venv/bin/activate

generate_resources() {
  name="$1"
  qrc="theme-$name.qrc"
  cd $name
  pyside6-rcc --project -o "$qrc"
  pyside6-rcc -g python "$qrc" -o "../../src/fk/desktop/theme_$name.py"
  rm "$qrc"
  cd ..
}

cd res
generate_resources "common"
generate_resources "light"
generate_resources "dark"
generate_resources "mixed"

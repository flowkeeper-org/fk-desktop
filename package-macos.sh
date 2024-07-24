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

set -e

# Step 0 - Enter venv
source venv/bin/activate

# Step 1 - Cleanup
rm -rf build dist Flowkeeper.dmg

# Step 2 - Create and sign an installer
pyinstaller installer/normal-build.spec -- --sign

# Step 3 - Create a DMG image
rm -rf dist/flowkeeper
create-dmg \
  --volname "Flowkeeper Installer" \
  --volicon "res/flowkeeper.icns" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Flowkeeper.app" 200 190 \
  --hide-extension "Flowkeeper.app" \
  --app-drop-link 600 185 \
  "Flowkeeper.dmg" \
  "dist/"

# Step 4 - Notarize the DMG
xcrun notarytool submit Flowkeeper.dmg --keychain-profile "notary-key" --wait

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

# In the next version(s) think of installing it in /opt/Flowkeeper instead

# 1. Get the version
echo "1. Version = $FK_VERSION"

# 2. Prepare temp folder
dist="build/deb"
rm -rf "$dist"
mkdir "$dist"
echo "2. Prepared temp folder"

# 3. Copy application files
mkdir -p "$dist/usr/lib/flowkeeper"
cp -r src/* "$dist/usr/lib/flowkeeper/"

mkdir -p "$dist/usr/share/icons/hicolor/1024x1024/apps"
mkdir -p "$dist/usr/share/icons/hicolor/48x48/apps"
cp res/flowkeeper.png "$dist/usr/share/icons/hicolor/1024x1024/apps/org.flowkeeper.Flowkeeper.png"
cp flowkeeper-48x48.png "$dist/usr/share/icons/hicolor/48x48/apps/org.flowkeeper.Flowkeeper.png"

mkdir -p "$dist/usr/bin"
cp scripts/linux/common/flowkeeper "$dist/usr/bin/flowkeeper"
echo "3. Copied application files"

# 4. Create a desktop shortcut
mkdir -p "$dist/usr/share/applications"
export FK_AUTOSTART_ARGS=""
< scripts/linux/common/org.flowkeeper.Flowkeeper.desktop envsubst > "$dist/usr/share/applications/org.flowkeeper.Flowkeeper.desktop"
echo "4. Created a desktop shortcut:"
cat "$dist/usr/share/applications/org.flowkeeper.Flowkeeper.desktop"

# 5. Create another one for autostart (with --autostart argument)
mkdir -p "$dist/etc/xdg/autostart"
export FK_AUTOSTART_ARGS="--autostart"
< scripts/linux/common/org.flowkeeper.Flowkeeper.desktop envsubst > "$dist/etc/xdg/autostart/org.flowkeeper.Flowkeeper.desktop"
echo "5. Added it to autostart"

# 6. Create metadata
mkdir "$dist/DEBIAN"
< scripts/linux/debian/debian-control-min envsubst > "$dist/DEBIAN/control"
echo "6. Created metadata"
cat "$dist/DEBIAN/control"

# 7. Build DEB file
dpkg-deb --build "$dist" dist/flowkeeper-min.deb
echo "7. Built DEB file"

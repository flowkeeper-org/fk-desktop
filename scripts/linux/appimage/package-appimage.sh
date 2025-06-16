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

# 1. Prepare temp folder
cd build
rm -rf AppDir
mkdir AppDir
echo "1. Prepared temp folder"

# 2. Copy application files
mkdir -p AppDir/usr/lib/flowkeeper
mkdir -p AppDir/usr/share/icons/hicolor/1024x1024/apps
mkdir -p AppDir/usr/share/icons/hicolor/48x48/apps
mkdir -p AppDir/usr/share/metainfo
mkdir -p AppDir/usr/share/applications
cp -r ../dist/standalone/* AppDir/usr/lib/flowkeeper/
cp ../res/flowkeeper.png AppDir/flowkeeper.png
cp ../res/flowkeeper.png AppDir/usr/share/icons/hicolor/1024x1024/apps/flowkeeper.png
cp ../flowkeeper-48x48.png AppDir/usr/share/icons/hicolor/48x48/apps/flowkeeper.png
cp ../scripts/linux/common/org.flowkeeper.Flowkeeper.metainfo.xml AppDir/usr/share/metainfo/org.flowkeeper.Flowkeeper.appdata.xml
echo "2. Copied application files"

# 3. Create a desktop shortcut
export FK_AUTOSTART_ARGS=""
< ../scripts/linux/common/flowkeeper.desktop envsubst > AppDir/flowkeeper.desktop
cp AppDir/flowkeeper.desktop AppDir/usr/share/applications
echo "3. Created a desktop shortcut:"
cat AppDir/flowkeeper.desktop

# 4. Create AppRun symlink
cd AppDir
ln -s ./usr/lib/flowkeeper/Flowkeeper ./AppRun
cd ..
echo "4. Created AppRun symlink"

# 5. Create .DirIcon symlink
cd AppDir
ln -s usr/share/icons/hicolor/1024x1024/apps/flowkeeper.png ./.DirIcon
cd ..
echo "5. Create .DirIcon symlink"

# 6. Build AppImage file
ls -al AppDir/
appimagetool AppDir
echo "6. Built AppImage file: $(ls ./*.AppImage)"

mv ./*.AppImage ../dist

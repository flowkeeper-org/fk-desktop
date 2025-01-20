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
VERSION_REGEX='^### v(.+) \(.*$'
VERSION_LINE=$(head --lines=1 res/CHANGELOG.txt)
if [[ $VERSION_LINE =~ $VERSION_REGEX ]]; then
	export FK_VERSION="${BASH_REMATCH[1]}"
else
	export FK_VERSION="N/A"
fi
echo "1. Version = $FK_VERSION"

# 2. Prepare temp folder
cd dist
rm -rf deb
mkdir deb
echo "2. Prepared temp folder"

# 3. Copy application files
mkdir -p deb/usr/local/lib/flowkeeper
cp -r flowkeeper/* deb/usr/local/lib/flowkeeper/
cp ../res/flowkeeper.png deb/usr/local/lib/flowkeeper/
echo "3. Copied application files"

# 4. Create a desktop shortcut
mkdir -p deb/usr/share/applications
export FK_AUTOSTART_ARGS=""
< ../installer/flowkeeper.desktop envsubst > deb/usr/share/applications/flowkeeper.desktop
echo "4. Created a desktop shortcut:"
cat deb/usr/share/applications/flowkeeper.desktop

# 5. Create another one for autostart (with --autostart argument)
mkdir -p deb/etc/xdg/autostart
export FK_AUTOSTART_ARGS="--autostart"
< ../installer/flowkeeper.desktop envsubst > deb/etc/xdg/autostart/flowkeeper.desktop
echo "5. Added it to autostart"

# 6. Create a relative symlink in /usr/local/bin
mkdir -p deb/usr/local/bin
cd deb/usr/local/bin
ln -s ../lib/flowkeeper/Flowkeeper ./flowkeeper
cd ../../../..
echo "6. Create a relative symlink in /usr/local/bin"

# 7. Create metadata
mkdir deb/DEBIAN
< ../installer/debian-control envsubst > deb/DEBIAN/control
echo "7. Created metadata"
cat deb/DEBIAN/control

# 8. Build DEB file
dpkg-deb --build deb flowkeeper.deb
echo "8. Built DEB file"

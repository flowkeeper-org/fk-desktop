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

# Adapted from https://apple.stackexchange.com/questions/402621/convert-png-image-icon-to-icns-file-macos
cd res
mkdir tmp.iconset
sips -z 16 16     flowkeeper-1024.png --out tmp.iconset/icon_16x16.png
sips -z 32 32     flowkeeper-1024.png --out tmp.iconset/icon_16x16@2x.png
sips -z 32 32     flowkeeper-1024.png --out tmp.iconset/icon_32x32.png
sips -z 64 64     flowkeeper-1024.png --out tmp.iconset/icon_32x32@2x.png
sips -z 128 128   flowkeeper-1024.png --out tmp.iconset/icon_128x128.png
sips -z 256 256   flowkeeper-1024.png --out tmp.iconset/icon_128x128@2x.png
sips -z 256 256   flowkeeper-1024.png --out tmp.iconset/icon_256x256.png
sips -z 512 512   flowkeeper-1024.png --out tmp.iconset/icon_256x256@2x.png
sips -z 512 512   flowkeeper-1024.png --out tmp.iconset/icon_512x512.png
cp flowkeeper-1024.png tmp.iconset/icon_512x512@2x.png
iconutil -c icns tmp.iconset
rm -R tmp.iconset
mv tmp.icns flowkeeper.icns

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

REPO="flowkeeper-org/fk-desktop"
OUTPUT="downloads"

mkdir -p "$OUTPUT"

if [ -z "$RELEASE" ]; then
    echo "Fetching the latest release..."
    echo Getting the latest release...
    RELEASE=$(gh release list --repo "$REPO" --json tagName,isPrerelease --jq ".[] | select(.isPrerelease) | .tagName")
else
    echo "Release variable is specified"
fi

echo "Downloading binaries for release $RELEASE to $(pwd)"

gh release download "$RELEASE" --clobber --dir "$OUTPUT" --pattern "*.exe" --repo "$REPO"
gh release download "$RELEASE" --clobber --dir "$OUTPUT" --pattern "*-windows-*-standalone.zip" --repo "$REPO"
echo "Done. Downloaded:"
ls -al "$OUTPUT"

echo "Unpacking standalone ZIPs"
for f in "$OUTPUT"/*.zip; do
  echo "Unpacking $f..."
  unzip -p "$OUTPUT/$f" "Flowkeeper.exe" > "$OUTPUT/$f.exe"
done

echo "Done. Extracted all:"
ls -al "$OUTPUT"


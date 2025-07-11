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

echo "Create the notary key"
xcrun notarytool store-credentials "notary-key" --apple-id "$NOTARIZATION_ID" --team-id "$NOTARIZATION_TEAM" --password "$NOTARIZATION_PASSWORD"

echo "Send the DMG for notarization"
xcrun notarytool submit "dist/Flowkeeper.dmg" --keychain-profile "notary-key" --wait

echo "Submission history"
xcrun notarytool log a65c29d5-dcff-48e5-a132-dc6c2b31cf84 --keychain-profile "notary-key"
xcrun notarytool info a65c29d5-dcff-48e5-a132-dc6c2b31cf84 --keychain-profile "notary-key"


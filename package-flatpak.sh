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

# IMPORTANT -- Here we assume that we built a DEB before, just for simplicity
# We can copy the pyinstaller results just as well

# 0. Install flatpak runtime and SDK
flatpak install -y flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

# 1. Build the image
cd dist
flatpak build-init flatpak org.flowkeeper.Flowkeeper org.kde.Sdk//6.6 org.kde.Platform//6.6
flatpak build flatpak cp -r deb/usr/local/* /app
flatpak build-finish flatpak --socket=x11 --share=network --command=flowkeeper
flatpak build-export repo flatpak

# Now we can archive dist/repo

# 2. Test
flatpak --user remote-add --no-gpg-verify --if-not-exists flowkeeper-repo repo
flatpak --user remove -y org.flowkeeper.Flowkeeper
flatpak --user install -y flowkeeper-repo org.flowkeeper.Flowkeeper
flatpak run org.flowkeeper.Flowkeeper

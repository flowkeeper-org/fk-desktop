#
# spec file for package flowkeeper
#
#  Flowkeeper - Pomodoro timer for power users and teams
#  Copyright (c) 2023 Constantine Kulak
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.


Name:           flowkeeper
Version:        0.10.0
Release:        0
Summary:        Pomodoro Technique desktop timer for power users
License:        GPL-3.0-only
Group:          Productivity/Text/Utilities
URL:            https://flowkeeper.org/
Source0:        https://github.com/flowkeeper-org/fk-desktop/release/fk-desktop-%{version}.tar.gz
BuildRequires:  python3-pyside6
BuildRequires:  python3-semantic_version
BuildRequires:  python3-cryptography
BuildRequires:  python3-keyring
Requires:       python3-pyside6
Requires:       python3-semantic_version
Requires:       python3-cryptography
Requires:       python3-keyring
BuildArch:      noarch

%description
Flowkeeper is a Pomodoro timer with a "classic" cross-platform UI paradigm
(desktop-first, no Electron). With its keyboard shortcuts and advanced settings,
Flowkeeper is optimized for power users. It stays as close as possible to the
Pomodoro Technique definition and format from the original book by Francesco
Cirillo.

Flowkeeper stores data in $XDG_DATA_HOME/Flowkeeper.

%prep
%setup -q -n "fk-desktop-%{version}"

%build
cd res
qrc="resources.qrc"
/usr/libexec/qt6/rcc --project -o "$qrc"
/usr/libexec/qt6/rcc -g python "$qrc" -o "../src/fk/desktop/resources.py"
rm "$qrc"

%install
mkdir -p "%{buildroot}%{_libexecdir}/flowkeeper"
cp -r src/* "%{buildroot}%{_libexecdir}/flowkeeper/"

mkdir -p "%{buildroot}%{_datadir}/icons/hicolor/1024x1024/apps"
mkdir -p "%{buildroot}%{_datadir}/icons/hicolor/48x48/apps"
cp -av res/flowkeeper.png "%{buildroot}%{_datadir}/icons/hicolor/1024x1024/apps/flowkeeper.png"
cp -av flowkeeper-48x48.png "%{buildroot}%{_datadir}/icons/hicolor/48x48/apps/flowkeeper.png"

mkdir -p "%{buildroot}%{_bindir}"
cp -av installer/flowkeeper "%{buildroot}%{_bindir}/flowkeeper"
echo "3. Copied application files"

mkdir -p "%{buildroot}%{_datadir}/applications"
export FK_AUTOSTART_ARGS=""
< installer/flowkeeper.desktop envsubst > "%{buildroot}%{_datadir}/applications/org.flowkeeper.Flowkeeper.desktop"

%check

%files
%doc README.md
%license LICENSE
%{_datadir}/applications/org.flowkeeper.Flowkeeper.desktop
%{_datadir}/icons/hicolor/
%{_libexecdir}/flowkeeper/
%{_bindir}/flowkeeper

%changelog
-------------------------------------------------------------------
Mon Feb 17 15:46:00 UTC 2025 - Constantine Kulak <contact@flowkeeper.org>

- Ability to track unfocused time, try to start a work item with no pomodoros (#94, #98).
- Ability to drag work items between backlogs (#60).
- Voided pomodoros are displayed as ticks, and completed ones are displayed as crosses to better match the Book (#41, #92).
- Hovering over pomodoros displays a detailed log of your work (#93).
- Flowkeeper window now hides automatically on auto-start (#102).
- Standard data and log directories are used on Linux, macOS and Windows (#65).
- Import from CSV, try Ctrl+I (#125).
- You can now find Flowkeeper on Flathub (#63).
- We now build Flowkeeper for ARM (arm64 / aarch64).
- We now build an AppImage binary for Flowkeeper.
- "Contact us" submenu to facilitate feedback collection (#111).
- [Technical] Added support for Qt 6.8.1.
- [Bugfix] Window icon on Wayland (#110).


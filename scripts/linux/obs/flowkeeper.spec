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
Version:        1.1.0
Release:        0
Summary:        Pomodoro backlog and timer for power users
License:        GPL-3.0-only
Group:          Productivity/Text/Utilities
URL:            https://flowkeeper.org/
Source0:        https://github.com/flowkeeper-org/fk-desktop/release/fk-desktop-%{version}.tar.gz
BuildRequires:  python3-pyside6-devel
BuildRequires:  python3-semantic_version
BuildRequires:  python3-cryptography
BuildRequires:  python3-keyring
Requires:       python3-pyside6
Requires:       python3-semantic_version
Requires:       python3-cryptography
Requires:       python3-keyring
BuildArch:      noarch

%description
Flowkeeper is a Pomodoro backlog and timer with a "classic" desktop-first UI paradigm. With its keyboard shortcuts and advanced settings, it is optimized for power users. It stays as close as possible to the Pomodoro Technique definition and format from the original book by Francesco Cirillo.

%prep
%setup -q -n "fk-desktop-%{version}"

%build
cd res
qrc="resources.qrc"
export PATH="$PATH:/usr/libexec/qt6:/usr/lib64/qt6/libexec"
rcc --project -o "$qrc"
rcc -g python "$qrc" -o "../src/fk/desktop/resources.py"
rm "$qrc"

# To speed up runtime
python3 -m compileall src

%install
mkdir -p "%{buildroot}%{_libexecdir}/flowkeeper"
cp -r src/* "%{buildroot}%{_libexecdir}/flowkeeper/"

mkdir -p "%{buildroot}%{_datadir}/icons/hicolor/"{48x48,1024x1024}"/apps"
cp -av flowkeeper-48x48.png "%{buildroot}%{_datadir}/icons/hicolor/48x48/apps/flowkeeper.png"
cp -av res/flowkeeper.png "%{buildroot}%{_datadir}/icons/hicolor/1024x1024/apps/"

mkdir -p "%{buildroot}%{_bindir}"
cp -av scripts/linux/common/flowkeeper "%{buildroot}%{_bindir}/flowkeeper"
echo "3. Copied application files"

mkdir -p "%{buildroot}%{_datadir}/applications"
export FK_AUTOSTART_ARGS=""
< scripts/linux/common/org.flowkeeper.Flowkeeper.desktop envsubst > "%{buildroot}%{_datadir}/applications/org.flowkeeper.Flowkeeper.desktop"

%check

%files
%doc README.md
%license LICENSE
%{_datadir}/applications/org.flowkeeper.Flowkeeper.desktop
%{_datadir}/icons/hicolor/
%{_libexecdir}/flowkeeper/
%{_bindir}/flowkeeper

%changelog

# Scripts

## Directory structure

- `.github/` - GitHub Actions pipelines definitions, not packaged
- `doc/` - Technical docs, not packaged
- `res/` - Resources, which are compiled to `src/fk/desktop/resources.py` using `generate-resources.sh`
  - `icons/` - In-program icons
  - `img/` -- For e2e testing only, can be stripped out
  - `sound/` -- Music and WAVs, packaged
  - `flowkeeper.icns` -- macOS icons, can be stripped out on Windows and Linux
  - * -- all other files needs to be packaged 
- `scripts/` - Build scripts for all operating systems, not packaged. See `README.md` in subdirectories.
- `src/` - PYTHONPATH for executing Flowkeeper, packaged
  - `fk/` 
    - `core/` - The core logic, which allows writing GUI and CLI apps. Only depends on `semantic-versioning`
    - `desktop/` - Qt windows, packaged
      - `desktop.py` - The entry point for Flowkeeper Desktop GUI
    - `e2e/` - End-to-end tests and screenshot generator scripts, not packaged
    - `qt/` - Qt-specific logic, including widgets, delegates, etc. Packaged.
    - `tests/` - Unit tests for `core/` module, not packaged
    - `tools/` - Command-line tools, mainly for testing, not packaged
      - `cli.py` - The entry point for Flowkeeper CLI, can be packaged with `core/` module
- `build/` - Temporary files created when building Flowkeeper packages, should be in `.gitignore`
  - `desktop.build` - Temp dir by Nuitka, can be deleted
  - `desktop.onefile.build` - Temp dir by Nuitka, can be deleted
  - `desktop.dist` - A standalone package by Nuitka, to be packaged
    - `Flowkeeper.bin` - The entry point for standalone build by Nuitka
    - * -- all other files are libraries
  - `Flowkeeper` - A one-file portable binary by Nuitka, to be packaged
- `dist/` - Resulting Flowkeeper building artifacts, should be in `.gitignore`
  - `standalone/` - Standalone build package, depending on the OS and compiler, which can be zipped
  - `flowkeeper-x.y.z-macOS-latest-nuitka-installer.dmg` - DMG built with Nuitka
  - `flowkeeper-x.y.z-macOS-latest-pyinstaller-installer.dmg` - DMG built with PyInstaller
  - `flowkeeper-x.y.z-macOS-latest-nuitka-portable` - macOS portable binary
  - `flowkeeper-x.y.z-windows-latest-nuitka-installer.exe` - Windows installer built with Nuitka
  - `flowkeeper-x.y.z-windows-latest-nuitka-portable.exe` - Windows portable EXE built with Nuitka
  - `flowkeeper-x.y.z-windows-latest-pyinstaller-installer.exe` - Windows installer built with PyInstaller
  - `flowkeeper-x.y.z-windows-latest-pyinstaller-portable.exe` - Windows portable EXE built with PyInstaller
  - `flowkeeper-x.y.z-ubuntu-latest-nuitka-min-package.deb`
  - `flowkeeper-x.y.z-ubuntu-latest-nuitka-package.deb`
  - `flowkeeper-x.y.z-ubuntu-latest-nuitka-portable`
  - `flowkeeper-x.y.z-ubuntu-latest-pyinstaller-min-package.deb`
  - `flowkeeper-x.y.z-ubuntu-latest-pyinstaller-package.deb`
  - `flowkeeper-x.y.z-ubuntu-latest-pyinstaller-portable`
- `venv/` - Virtual env for building purposes, in `.gitignore`
- `README.md` - The main README file, not packaged
- `requirements.txt` - Requirements file for running, building and testing Flowkeeper, not packaged
- `run.sh` - A convenience shell script for running Flowkeeper in dev environment, not packaged
- `run-tests.sh` - A convenience shell script for unit tests, not packaged
- `LICENSE` - GPLv3 license file

## Installing dependencies for build

All operating systems:

- Install Git
- Install Python 3.11 for Qt 6.7, or 3.12+ for 6.8

Windows:

- Install InnoSetup: `scripts/windows/install-innosetup.sh`

macOS:

- Install create-dmg utility and provision certificates for signing code. This requires env 
variables and secrets only available in GitHub Actions. When building locally you don't 
have to run `install-certificates.sh`.

```bash
scripts/macos/install-create-dmg.sh
scripts/macos/install-certificates.sh
```

Linux:

Install AppImage Tool:

```bash
scripts/linux/appimage/install-appimage.sh
```

## Building

Note that all commands here are Bash. On Windows you have to use Git Bash, not WSL. Otherwise,
build scripts won't be able to detect Windows environment.

### Create a virtual environment and install Python requirements: 

Linux and macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-build.txt
```

Windows:

```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements-build.txt
```

### Generate resources

This will create `src/fk/desktop/resources.py` and `flowkeeper.icns` for macOS.

```bash
scripts/common/generate-resources.sh
```

### Create binary packages

TODO: Complete this section

With Nuitka: ``

With PyInstaller: ``
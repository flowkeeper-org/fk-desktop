# To do before release

1. "Compress" doesn't support long breaks
2. Test if "Repair" and "Import" support everything correctly. Create unit tests for all of those.
3. Labels in Settings are not tall enough on Windows 
4. Fonts -- backlogs use default font 
5. Fonts -- status uses default font 
6. Fonts -- focus mode uses default font. Default focus becomes the same after double-clicking. 
7. Tray icon doesn't work after changing the flavor while running a pomodoro 
8. Backlogs toggle icon doesn't change its color on theme change 
9. Rows height doesn't recalculate on fonts change

# Tests

## Windows binaries

1. No sound on Windows with Nuitka
2. "standalone" directory in ZIPs 
3. Sign binaries in standalone ZIPs and repack

## Linux binaries

1. KUbuntu 24.04 doesn't support deb-min installer (Qt 6.4.2 max, same for Debian)
2. Ubuntu 22.04 ships with Qt 6.2.4 (Universe repo) -- check all for Pyside6
3. The "fat" versions has GTK / default theme
4. No sound for Nuitka, same as Windows
5. Keyboard doesn't work with PyInstaller binaries on openSUSE -- both 22 and 24

### AppImage

### Flatpak

### openSUSE installer

## macOS binaries

1. On Ventura 13 / x86 and ARM, both Nuitka and PyInstaller -- no signature
2. "Too many values to unpack" when launching Settings, even after settings reset
3. No sound for Nuitka, same as Windows

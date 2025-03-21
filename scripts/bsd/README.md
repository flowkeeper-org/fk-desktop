# Building for FreeBSD

We successfully built and tested Flowkeeper on FreeBSD:

```
pkg install python3 git devel/pyside6 devel/pyside6-tools py311-keyring py311-semantic-version
git clone https://github.com/flowkeeper-org/fk-desktop.git
cd fk-desktop/res
/usr/local/bin/pyside6/rcc --project -o resources.qrc
/usr/local/bin/pyside6/rcc -g python resources.qrc -o ../src/fk/desktop/resources.py
cd ..
PYTHONPATH=src python3.11 -m fk.desktop.desktop
```

Tested with:

- KDE 5.27.11 on X11
- FreeBSD 14.1 RELEASE
- Flowkeeper v0.10.0
- Python 3.11.11
- Qt 6.8.2 (xcb)

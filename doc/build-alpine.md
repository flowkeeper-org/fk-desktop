# Building for Alpine Linux

Flowkeeper's CI pipeline runs PyInstaller on Ubuntu and thus generates binaries which rely on glibc. 
Alpine is based on musl, so you'd get "symbol not found" errors in runtime if you try to run any of the
"official" binaries.

You can still use Flowkeeper with Alpine. We tested it with the edge release + Xfce. Instructions:

1. Install `py3-pyside6` package via `apk`. This is the only tricky bit. We couldn't install PySide6 
via pip from inside the venv, as we'd normally do.
2. Clone this repo and create a Python Virtual Environment, *which uses system packages*:
`python3 -m venv venv --system-site-packages`
3. The rest of the steps are the same as for any other Linux OS


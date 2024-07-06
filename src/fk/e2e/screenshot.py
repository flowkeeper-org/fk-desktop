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
from __future__ import annotations

import logging
import os
import random
import subprocess
from typing import Callable

from PIL import Image
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class Screenshot:
    _method: Callable[[str], None]

    def __init__(self):
        self._method = None
        for m in [
            Screenshot._take_scrot,
            Screenshot._take_gnome_screenshot,
            Screenshot._take_xfce4_screenshooter,
            Screenshot._take_imagemagick,
            Screenshot._take_xwd,
            Screenshot._take_flameshot,
            Screenshot._take_ksnip,
            Screenshot._take_spectacle,
            Screenshot._take_nircmd,
            Screenshot._take_powershell,
            Screenshot._take_screencapture,
        ]:
            file = f'test-results/check-{random.randint(100000, 999999)}.png'
            try:
                m(file)
                im = Image.open(file)
                if im.getbbox():
                    logger.info(f'Screenshot method {m.__name__} works')
                    self._method = m
                    break
                else:
                    logger.warning(f'Taking screenshot via {m.__name__} resulted in an empty image')
            except Exception as e:
                logger.warning(f'Taking screenshot via {m.__name__} failed')
            finally:
                if os.path.exists(file):
                    os.unlink(file)

    def take_screen(self, name: str) -> str:
        if self._method is None:
            logger.warning(f'Tried to take screenshot {name}, but couldn\'t find how to do it')
        else:
            filename = f'test-results/{name}-full.png'
            logger.debug(f'Taking full-screen screenshot {filename} via {self._method.__name__}')
            return self._method(filename)

    def take_window(self, name: str, window: QWidget) -> str:
        if self._method is None:
            logger.warning(f'Tried to take screenshot {name}, but couldn\'t find how to do it')
        else:
            filename = f'test-results/{name}-window.png'
            logger.debug(f'Taking screenshot {filename} of window {window.objectName()} via {self._method.__name__}')
            window.grab().save(filename)

    @staticmethod
    def _take_scrot(filename: str) -> None:
        subprocess.run(["scrot",
                        "--silent",
                        "--overwrite",
                        filename])

    @staticmethod
    def _take_imagemagick(filename: str) -> None:
        subprocess.run(["import",
                        "-window",
                        "root",
                        filename])

    @staticmethod
    def _take_gnome_screenshot(filename: str) -> None:
        subprocess.run(["gnome-screenshot",
                        "-f",
                        filename])

    @staticmethod
    def _take_flameshot(filename: str) -> None:
        with open(filename, "w") as file:
            subprocess.run(["flameshot",
                        "screen",
                        "-r"], stdout=file)

    @staticmethod
    def _take_xwd(filename: str) -> None:
        subprocess.run(["xwd",
                        "-root",
                        "-out",
                        filename])
        subprocess.run(["convert",
                        f"xwd:{filename}",
                        filename])

    @staticmethod
    def _take_xfce4_screenshooter(filename: str) -> None:
        subprocess.run(["xfce4-screenshooter",
                        "--fullscreen",
                        "--save",
                        filename])

    @staticmethod
    def _take_ksnip(filename: str) -> None:
        subprocess.run(["ksnip",
                        "--fullscreen",
                        "--saveto",
                        filename])

    @staticmethod
    def _take_spectacle(filename: str) -> None:
        subprocess.run(["spectacle",
                        "--fullscreen",
                        "--background",
                        "--nonotify",
                        "--output",
                        filename])

    @staticmethod
    def _take_screencapture(filename: str) -> None:
        subprocess.run(["screencapture",
                        filename])

    @staticmethod
    def _take_nircmd(filename: str) -> None:
        subprocess.run(["nircmdc",
                        "savescreenshot",
                        filename])

    @staticmethod
    def _take_powershell(filename: str, window_id: int | None = None) -> None:
        ps = f'''
            [Reflection.Assembly]::LoadWithPartialName("System.Drawing")
            function screenshot([Drawing.Rectangle]$bounds, $path) {{
               $bmp = New-Object Drawing.Bitmap $bounds.width, $bounds.height
               $graphics = [Drawing.Graphics]::FromImage($bmp)
            
               $graphics.CopyFromScreen($bounds.Location, [Drawing.Point]::Empty, $bounds.size)
            
               $bmp.Save($path)
            
               $graphics.Dispose()
               $bmp.Dispose()
            }}
            
            $bounds = [Drawing.Rectangle]::FromLTRB(0, 0, 1000, 900)
            screenshot $bounds "{filename}"
        '''
        subprocess.run(["powershell",
                        "-Command",
                        ps])


if __name__ == "__main__":
    s = Screenshot()
    s.take_screen('test')

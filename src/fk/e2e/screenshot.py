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

logger = logging.getLogger(__name__)


class Screenshot:
    _method: Callable[[str, str | None], None]

    def __init__(self):
        self._method = None
        for m in [
            Screenshot._take_gnome_screenshot,
            Screenshot._take_xfce4_screenshooter,
            Screenshot._take_xwd,
            Screenshot._take_scrot,
            Screenshot._take_imagemagick,
            Screenshot._take_flameshot,
            Screenshot._take_ksnip,
            Screenshot._take_spectacle,
            Screenshot._take_nircmd,
            Screenshot._take_powershell,
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

    def take(self, name: str, window_id: int | None = None) -> str:
        if self._method is None:
            logger.warning(f'Tried to take screenshot {name}, but couldn\'t find how to do it')
        else:
            filename = f'test-results/{name}.png'
            logger.debug(f'Taking screenshot {filename} / {window_id} via {self._method.__name__}')
            return self._method(filename, window_id)

    @staticmethod
    def _take_scrot(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["scrot",
                            "--silent",
                            "--overwrite",
                            filename])
        else:
            subprocess.run(["scrot",
                            "--silent",
                            "--overwrite",
                            "--focused",
                            "--border",
                            filename])

    @staticmethod
    def _take_imagemagick(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["import",
                            "-window",
                            "root",
                            filename])
        else:
            subprocess.run(["import",
                            "-border",
                            "-window",
                            str(window_id),
                            filename])

    @staticmethod
    def _take_gnome_screenshot(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["gnome-screenshot",
                            "-f",
                            filename])
        else:
            subprocess.run(["gnome-screenshot",
                            "--window",
                            "--include-border",
                            "-f",
                            filename])

    @staticmethod
    def _take_flameshot(filename: str, window_id: int | None = None) -> None:
        with open(filename, "w") as file:
            subprocess.run(["flameshot",
                        "screen",
                        "-r"], stdout=file)
        if window_id is not None:
            # TODO: Crop the screenshot here
            pass

    @staticmethod
    def _take_xwd(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["xwd",
                            "-root",
                            "-out",
                            filename])
        else:
            subprocess.run(["xwd",
                            "-id",
                            str(window_id),
                            "-out",
                            filename])
        subprocess.run(["convert",
                        f"xwd:{filename}",
                        filename])

    @staticmethod
    def _take_xfce4_screenshooter(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["xfce4-screenshooter",
                            "--fullscreen",
                            "--save",
                            filename])
        else:
            subprocess.run(["xfce4-screenshooter",
                            "--window",
                            "--save",
                            filename])

    @staticmethod
    def _take_ksnip(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["ksnip",
                            "--fullscreen",
                            "--saveto",
                            filename])
        else:
            subprocess.run(["ksnip",
                            "--active",
                            "--saveto",
                            filename])

    @staticmethod
    def _take_spectacle(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["spectacle",
                            "--fullscreen",
                            "--background",
                            "--nonotify",
                            "--output",
                            filename])
        else:
            subprocess.run(["spectacle",
                            "--activewindow",
                            "--background",
                            "--nonotify",
                            "--output",
                            filename])

    @staticmethod
    def _take_nircmd(filename: str, window_id: int | None = None) -> None:
        if window_id is None:
            subprocess.run(["nircmdc",
                            "savescreenshot",
                            filename])
        else:
            subprocess.run(["nircmdc",
                            "savescreenshotwin",
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
